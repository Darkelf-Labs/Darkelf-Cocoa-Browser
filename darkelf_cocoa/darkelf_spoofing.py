from WebKit import (
    WKUserScript,
    WKUserScriptInjectionTimeAtDocumentStart,
)


# ============================================================
# SCREEN SPOOFING
# ============================================================

def inject_screen_spoof(ucc):

    js = r"""
    (() => {

        const width = 1920;
        const height = 1080;

        const define = (obj, prop, value) => {

            try {

                Object.defineProperty(obj, prop, {
                    get: () => value,
                    configurable: true
                });

            } catch (e) {}
        };

        const patch = () => {

            // ------------------------------------------------
            // Screen
            // ------------------------------------------------

            define(Screen.prototype, "width", width);
            define(Screen.prototype, "height", height);

            define(Screen.prototype, "availWidth", width);
            define(Screen.prototype, "availHeight", height - 37);

            // ------------------------------------------------
            // Window
            // ------------------------------------------------

            // ------------------------------------------------
            // window.screen
            // ------------------------------------------------

            define(window.screen, "width", width);
            define(window.screen, "height", height);

            define(window.screen, "availWidth", width);
            define(window.screen, "availHeight", height - 37);

            // ------------------------------------------------
            // window
            // ------------------------------------------------

            // Keep live viewport geometry native for responsive layout and challenges.
        };

        // initial patch
        patch();

        // DOM ready
        document.addEventListener(
            "DOMContentLoaded",
            patch,
            { once: true }
        );

        // load complete
        window.addEventListener(
            "load",
            patch,
            { once: true }
        );

    })();
    """

    script = (
        WKUserScript.alloc()
        .initWithSource_injectionTime_forMainFrameOnly_(
            js,
            WKUserScriptInjectionTimeAtDocumentStart,
            False
        )
    )

    ucc.addUserScript_(script)
