#!/usr/bin/env python3
"""
Darkelf Enhanced WebKit / PyObjC Security Auditor v8.4
- Syntax-fixed
- Recursive project scanning
"""

from pathlib import Path
import argparse
import ast
import json
import os
import re

GOOD_RULES = [
    (r"nonPersistentDataStore","Ephemeral WKWebsiteDataStore"),
    (r"ephemeralSessionConfiguration","Ephemeral NSURLSession"),
    (r"setNavigationDelegate_","Navigation delegate configured"),
    (r"setUIDelegate_","UI delegate configured"),
    (r"setProcessPool_","Explicit WKProcessPool"),
    (r"WKContentRuleListStore","Content Rule List"),
    (r"requestMediaCapturePermission","Media permission delegate"),
    (r"decisionHandler\(0\)","Media capture denied"),
]

SAFE_KVC={
    "developerExtrasEnabled",
    "allowFileAccessFromFileURLs",
    "allowUniversalAccessFromFileURLs",
    "javaScriptCanOpenWindowsAutomatically",
    "logsPageMessagesToSystemConsoleEnabled",
}

TRUSTED=("_build_","_render_","HOME_HTML","REPORT_HTML","ABOUT_HTML","CONSOLE_HTML")
UNTRUSTED=("requests.","urllib","socket","input(","pasteboard","clipboard")

TAINT_SOURCES = {
    "input",
    "requests",
    "urllib",
    "socket",
    "clipboard",
    "pasteboard",
}

def normalize_selector(name:str)->str:
    return re.sub(r"_[^_]*Handler_?$","",name)

def discover_python_files(target):
    p=Path(target)
    if p.is_file():
        return [p]
    files=[]
    skip={"__pycache__",".git",".venv","venv","env","build","dist",".mypy_cache",".pytest_cache"}
    for root,dirs,names in os.walk(p):
        dirs[:]=[d for d in dirs if d not in skip]
        for n in names:
            if n.endswith(".py"):
                files.append(Path(root)/n)
    return sorted(files)
    
class WebKitVisitor(ast.NodeVisitor):
    def __init__(self):
        self.assignments = {}
        self.tainted = set()
        self.findings = []

    def _mark_tainted(self, name):
        if name:
            self.tainted.add(name)

    def visit_Assign(self, node):
        if len(node.targets) != 1:
            self.generic_visit(node)
            return

        target = node.targets[0]

        if not isinstance(target, ast.Name):
            self.generic_visit(node)
            return

        name = target.id
        self.assignments[name] = node.value

        # Direct taint source
        if isinstance(node.value, ast.Call):
            func = node.value.func

            if isinstance(func, ast.Name):
                if func.id in TAINT_SOURCES:
                    self._mark_tainted(name)

            elif isinstance(func, ast.Attribute):
                if func.attr in TAINT_SOURCES:
                    self._mark_tainted(name)

        # Propagate taint
        elif isinstance(node.value, ast.Name):
            if node.value.id in self.tainted:
                self._mark_tainted(name)

        self.generic_visit(node)

    def visit_Call(self, node):

        if isinstance(node.func, ast.Attribute):

            method = node.func.attr

            #
            # evaluateJavaScript_
            #

            if method == "evaluateJavaScript_":

                if node.args:

                    arg = node.args[0]

                    if isinstance(arg, ast.Name):

                        if arg.id in self.tainted:

                            self.findings.append(
                                (
                                    node.lineno,
                                    "HIGH",
                                    "evaluateJavaScript() uses tainted variable",
                                )
                            )

                    elif isinstance(arg, ast.JoinedStr):

                        self.findings.append(
                            (
                                node.lineno,
                                "HIGH",
                                "Dynamic f-string JavaScript",
                            )
                        )

                    elif isinstance(arg, ast.BinOp):

                        self.findings.append(
                            (
                                node.lineno,
                                "HIGH",
                                "Concatenated JavaScript",
                            )
                        )

            #
            # loadHTMLString_
            #

            elif method == "loadHTMLString_":

                if node.args:

                    arg = node.args[0]

                    if isinstance(arg, ast.Name):

                        if arg.id in self.tainted:

                            self.findings.append(
                                (
                                    node.lineno,
                                    "HIGH",
                                    "loadHTMLString() uses tainted HTML",
                                )
                            )

            #
            # WKUserScript
            #

            elif method == "initWithSource_injectionTime_forMainFrameOnly_":

                self.findings.append(
                    (
                        node.lineno,
                        "INFO",
                        "WKUserScript created",
                    )
                )

        self.generic_visit(node)

def ast_scan(source_text):
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []

    visitor = WebKitVisitor()
    visitor.visit(tree)
    return visitor.findings
    
def scan(lines):
    findings={k:[] for k in ("GOOD","INFO","MEDIUM","HIGH")}
    score=100
    seen=set()
    joined="\n".join(lines)
    ast_findings = ast_scan(joined)
    tainted=set()
    html_vars={}
    def add(cat,line,msg):
        nonlocal score
        key=(cat,line,msg)
        if key in seen:
            return
        seen.add(key)
        conf={"GOOD":"High","INFO":"Medium","MEDIUM":"Medium","HIGH":"High"}[cat]
        findings[cat].append((line,msg,conf))
        if cat=="HIGH":
            score-=10
        elif cat=="MEDIUM":
            score-=3
    for i,line in enumerate(lines,1):
        m=re.match(r"\s*([A-Za-z_]\w*)\s*=\s*(.+)", line)
        if m:
            var,expr=m.group(1),m.group(2)
            html_vars[var]=expr
            if any(s in expr for s in TAINT_SOURCES):
                tainted.add(var)
            for t in list(tainted):
                if t in expr:
                    tainted.add(var)

        for pat,msg in GOOD_RULES:
            if re.search(pat,line):
                add("GOOD",i,msg)
        if "setValue_forKey_" in line:
            m=re.search(r'"([^"]+)"',line)
            key=m.group(1) if m else "unknown"
            if key in SAFE_KVC:
                add("INFO",i,f"Known WebKit KVC: {key}")
            else:
                add("MEDIUM",i,f"Review KVC key: {key}")
        if "loadHTMLString_" in line:
            window="\n".join(lines[max(0,i-40):min(len(lines),i+5)])
            if any(t in window for t in TRUSTED):
                add("GOOD",i,"Trusted internal HTML")
            elif any(t in window for t in UNTRUSTED):
                add("HIGH",i,"HTML appears to originate from untrusted source")
            else:
                add("INFO",i,"loadHTMLString() (assumed internal)")
        if "evaluateJavaScript_" in line:
            if any(x in line for x in ('f"',"format(","+","%")):
                add("HIGH",i,"Dynamic JavaScript execution")
            else:
                add("INFO",i,"Static evaluateJavaScript()")

        if "evaluateJavaScript_" in line:
            risky = (
                any(x in line for x in ('f"', "format(", "+", "%"))
                or
                any(v in line for v in tainted)
            )
            if risky:
                add("HIGH",i,"evaluateJavaScript() uses tainted input")
        if "loadHTMLString_" in line:
            for n,v in html_vars.items():
                if n in line and any(u in v for u in UNTRUSTED):
                    add("HIGH",i,"loadHTMLString() fed by untrusted HTML")
        if "userContentController_didReceiveScriptMessage_" in line:
            add("GOOD",i,"WKScriptMessageHandler implemented")
        if "WKUserScript" in line:
            add("INFO",i,"WKUserScript detected")
        if "startURLSchemeTask" in line or "webView_startURLSchemeTask_" in line:
            add("GOOD",i,"WKURLSchemeHandler implemented")
        if "WKWebpagePreferences" in line:
            add("INFO",i,"WKWebpagePreferences configured")
        if "allowsContentJavaScript" in line:
            if "False" in line:
                add("GOOD",i,"JavaScript disabled")
            elif "True" in line:
                add("INFO",i,"JavaScript enabled")
        if "loadFileURL_allowingReadAccessToURL_" in line:
            add("INFO",i,"Local file loading")
    normalized="\n".join(normalize_selector(x) for x in lines)
    for selector in ("decidePolicyForNavigationAction","requestMediaCapturePermission","createWebViewWithConfiguration"):
        if selector in joined or selector in normalized:
            add("GOOD",0,f"Delegate implements {selector}")
    for line, severity, message in ast_findings:
        add(severity, line, message)
    return max(score,0),findings
    
    
RULE_IDS = {
    "Dynamic JavaScript execution": "DEW001",
    "evaluateJavaScript() uses tainted input": "DEW002",
    "evaluateJavaScript() uses tainted variable": "DEW003",
    "Dynamic f-string JavaScript": "DEW004",
    "Concatenated JavaScript": "DEW005",
    "loadHTMLString() uses tainted HTML": "DEW006",
    "loadHTMLString() fed by untrusted HTML": "DEW007",
    "HTML appears to originate from untrusted source": "DEW008",
    "Local file loading": "DEW011",
    "WKUserScript detected": "DEW012",
    "WKUserScript created": "DEW013",
    "WKWebpagePreferences configured": "DEW014",
    "JavaScript enabled": "DEW015",
    "JavaScript disabled": "DEW016",
}

def get_rule_id(message):
    if message.startswith("Review KVC key:"):
        return "DEW009"

    if message.startswith("Known WebKit KVC:"):
        return "DEW010"

    return RULE_IDS.get(message, "DEW999")

def write_sarif(results, output_file):
    """Write SARIF 2.1.0 report."""

    level_map = {
        "HIGH": "error",
        "MEDIUM": "warning",
        "INFO": "note",
        "GOOD": "none",
    }

    sarif = {
        "version": "2.1.0",
        "$schema":
            "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name":
                            "Darkelf WebKit Security Audit",
                        "version":
                            "8.4",
                        "informationUri":
                            "https://github.com/Darkelf2024",
                        "rules": [],
                    }
                },
                "results": [],
            }
        ],
    }

    rules = {}
    sarif_results = []

    for file in results:

        filename = file["file"]

        for severity in (
            "HIGH",
            "MEDIUM",
            "INFO",
            "GOOD",
        ):

            for line, message, _ in file["findings"][severity]:

                rule_id = get_rule_id(message)

                if rule_id not in rules:

                    rules[rule_id] = {
                        "id": rule_id,
                        "name": message,
                        "shortDescription": {
                            "text": message
                        },
                    }

                sarif_results.append(
                    {
                        "ruleId": rule_id,
                        "level": level_map[severity],
                        "message": {
                            "text": message
                        },
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {
                                        "uri": filename
                                    },
                                    "region": {
                                        "startLine": max(
                                            line,
                                            1,
                                        )
                                    },
                                }
                            }
                        ],
                    }
                )

    sarif["runs"][0]["tool"]["driver"]["rules"] = list(
        rules.values()
    )

    sarif["runs"][0]["results"] = sarif_results

    with open(output_file, "w") as f:
        json.dump(sarif, f, indent=2)
        
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--sarif",
        metavar="FILE",
        help="Write SARIF 2.1.0 report",
    )

    args = ap.parse_args()

    files = discover_python_files(args.target)

    results = []
    total = 0

    for f in files:
        try:
            lines = f.read_text(errors="ignore").splitlines()
        except Exception:
            continue

        score, findings = scan(lines)

        total += score

        results.append(
            {
                "file": str(f),
                "score": score,
                "findings": findings,
            }
        )

    project = total // len(results) if results else 0

    #
    # Write SARIF if requested
    #

    if args.sarif:
        write_sarif(results, args.sarif)

    #
    # Count HIGH findings
    #

    high = sum(
        len(r["findings"]["HIGH"])
        for r in results
    )

    #
    # JSON mode
    #

    if args.json:
        print(
            json.dumps(
                {
                    "project_score": project,
                    "files": results,
                },
                indent=2,
            )
        )

        # GitHub Actions can still fail after JSON output
        if high:
            raise SystemExit(1)

        return

    #
    # Console report
    #

    print("=" * 70)
    print("Enhanced WebKit / PyObjC Security Audit v8.4")
    print("=" * 70)
    print(f"Files scanned : {len(results)}")
    print(f"Project Score : {project}/100")
    print(f"HIGH Findings : {high}")

    for r in results:

        print("\n" + "-" * 70)
        print(r["file"])
        print("-" * 70)

        for cat in (
            "GOOD",
            "INFO",
            "MEDIUM",
            "HIGH",
        ):

            items = r["findings"][cat]

            if not items:
                continue

            print(f"\n{cat}:")

            for ln, msg, conf in items:

                prefix = (
                    f"Line {ln}: "
                    if ln
                    else ""
                )

                print(
                    f" - {prefix}{msg} [{conf}]"
                )

        print(f"\nFile Score: {r['score']}/100")

    #
    # Fail CI only after all reports have been printed
    #

    if high:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
