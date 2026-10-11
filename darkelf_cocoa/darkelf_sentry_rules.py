"""Optional isolated WebKit rule list for Sentry CDN scripts.

Does not modify Darkelf's existing v15.11 content rules.
"""

import json
from WebKit import WKContentRuleListStore
from PyObjCTools import AppHelper


class SentryRuleManager:
    IDENTIFIER = "darkelf_sentry_script_v1"
    _rule_list = None
    _started = False
    _pending = []

    @classmethod
    def load_rules(cls):
        if cls._started:
            return
        cls._started = True
        store = WKContentRuleListStore.defaultStore()

        def ready(rule_list, error):
            if rule_list is None:
                print("[SentryRules] Failed to compile/load:", error, flush=True)
                return
            cls._rule_list = rule_list

            def attach_pending():
                pending, cls._pending = cls._pending, []
                for controller in pending:
                    try:
                        controller.addContentRuleList_(rule_list)
                    except Exception as exc:
                        print("[SentryRules] Attachment failed:", exc, flush=True)

            AppHelper.callAfter(attach_pending)

        def lookup(rule_list, error):
            if rule_list is not None:
                ready(rule_list, None)
                return
            rules = [
                {
                    "trigger": {
                        "url-filter": r"^https?://js\.sentry-cdn\.com/",
                        "resource-type": ["script"],
                    },
                    "action": {"type": "block"},
                },
                {
                    "trigger": {
                        "url-filter": r"^https?://browser\.sentry-cdn\.com/",
                        "resource-type": ["script"],
                    },
                    "action": {"type": "block"},
                },
            ]
            store.compileContentRuleListForIdentifier_encodedContentRuleList_completionHandler_(
                cls.IDENTIFIER, json.dumps(rules), ready
            )

        store.lookUpContentRuleListForIdentifier_completionHandler_(cls.IDENTIFIER, lookup)

    @classmethod
    def attach_to_controller(cls, controller):
        if cls._rule_list is not None:
            controller.addContentRuleList_(cls._rule_list)
        elif controller not in cls._pending:
            cls._pending.append(controller)
