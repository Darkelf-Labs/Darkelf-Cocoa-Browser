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
        const dpr = 2;

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

            define(Window.prototype, "innerWidth", width);
            define(Window.prototype, "innerHeight", height);

            define(Window.prototype, "outerWidth", width);
            define(Window.prototype, "outerHeight", height);

            define(Window.prototype, "devicePixelRatio", dpr);

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

            define(window, "innerWidth", width);
            define(window, "innerHeight", height);

            define(window, "outerWidth", width);
            define(window, "outerHeight", height);

            define(window, "devicePixelRatio", dpr);

            // ------------------------------------------------
            // visual viewport
            // ------------------------------------------------

            if (window.visualViewport) {

                define(window.visualViewport, "width", width);

                define(window.visualViewport, "height", height);

                define(window.visualViewport, "scale", 1);
            }
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
