import objc

from Cocoa import (
    NSView,
    NSButton,
    NSTextField,
    NSColor,
    NSMakeRect,
)

from AppKit import (
    NSFont,
    NSAnimationContext,
    NSViewWidthSizable,
    NSViewMinXMargin,
    NSViewMaxYMargin,
)


# ============================================================
# Download Progress View
# ============================================================

class DownloadProgressView(NSView):

    # --------------------------------------------------------
    # Init
    # --------------------------------------------------------

    def initWithFrame_(self, frame):

        self = (
            objc.super(
                DownloadProgressView,
                self
            ).initWithFrame_(frame)
        )

        if self is None:
            return None

        # ------------------------------------------------
        # force proper sizing
        # ------------------------------------------------

        height = 60

        self.setFrame_(
            NSMakeRect(
                frame.origin.x,
                0,
                frame.size.width,
                height
            )
        )

        # bottom anchored
        self.setAutoresizingMask_(
            NSViewWidthSizable
            | NSViewMaxYMargin
        )

        self.setWantsLayer_(True)

        self.layer().setCornerRadius_(12)

        self.layer().setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.04,
                0.05,
                0.07,
                1
            ).CGColor()
        )

        # ------------------------------------------------
        # filename label
        # ------------------------------------------------

        self.label = NSTextField.alloc().initWithFrame_(
            NSMakeRect(
                15,
                40,
                300,
                20
            )
        )

        self.label.setBezeled_(False)
        self.label.setEditable_(False)
        self.label.setDrawsBackground_(False)

        self.label.setTextColor_(
            NSColor.whiteColor()
        )

        self.label.setFont_(
            NSFont.systemFontOfSize_(13)
        )

        self.addSubview_(self.label)

        # ------------------------------------------------
        # percent label
        # ------------------------------------------------

        self.percent = NSTextField.alloc().initWithFrame_(
            NSMakeRect(
                frame.size.width - 90,
                40,
                60,
                20
            )
        )

        self.percent.setAutoresizingMask_(
            NSViewMinXMargin
        )

        self.percent.setBezeled_(False)
        self.percent.setEditable_(False)
        self.percent.setDrawsBackground_(False)

        self.percent.setTextColor_(
            NSColor.systemGrayColor()
        )

        self.percent.setFont_(
            NSFont.systemFontOfSize_(12)
        )

        self.percent.setAlignment_(2)

        self.percent.setStringValue_("0%")

        self.addSubview_(self.percent)

        # ------------------------------------------------
        # done button
        # ------------------------------------------------

        self.done = NSButton.alloc().initWithFrame_(
            NSMakeRect(
                frame.size.width - 90,
                18,
                70,
                22
            )
        )

        self.done.setAutoresizingMask_(
            NSViewMinXMargin
        )

        self.done.setTitle_("Done")

        self.done.setBezelStyle_(1)

        self.done.setTarget_(self)

        self.done.setAction_("closeDownload:")

        self.addSubview_(self.done)

        # ------------------------------------------------
        # progress track
        # ------------------------------------------------

        self.progressTrack = NSView.alloc().initWithFrame_(
            NSMakeRect(
                15,
                22,
                frame.size.width - 120,
                6
            )
        )

        self.progressTrack.setAutoresizingMask_(
            NSViewWidthSizable
        )

        self.progressTrack.setWantsLayer_(True)

        self.progressTrack.layer().setCornerRadius_(3)

        self.progressTrack.layer().setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.08,
                0.09,
                0.12,
                1
            ).CGColor()
        )

        self.addSubview_(self.progressTrack)

        # ------------------------------------------------
        # progress fill
        # ------------------------------------------------

        self.progressFill = NSView.alloc().initWithFrame_(
            NSMakeRect(
                0,
                0,
                0,
                6
            )
        )

        self.progressFill.setAutoresizingMask_(
            NSViewWidthSizable
        )

        self.progressFill.setWantsLayer_(True)

        green = (
            NSColor.colorWithCalibratedRed_green_blue_alpha_(
                0.20,
                0.78,
                0.35,
                1
            )
        )

        self.progressFill.layer().setCornerRadius_(3)

        self.progressFill.layer().setBackgroundColor_(
            green.CGColor()
        )

        self.progressFill.layer().setShadowColor_(
            green.CGColor()
        )

        self.progressFill.layer().setShadowOpacity_(0.7)

        self.progressFill.layer().setShadowRadius_(6)

        self.progressFill.layer().setShadowOffset_((0, 0))

        self.progressTrack.addSubview_(self.progressFill)

        # ------------------------------------------------
        # speed label
        # ------------------------------------------------

        self.speed = NSTextField.alloc().initWithFrame_(
            NSMakeRect(
                15,
                2,
                200,
                15
            )
        )

        self.speed.setBezeled_(False)
        self.speed.setEditable_(False)
        self.speed.setDrawsBackground_(False)

        self.speed.setTextColor_(
            NSColor.systemGrayColor()
        )

        self.speed.setFont_(
            NSFont.systemFontOfSize_(11)
        )

        self.addSubview_(self.speed)

        return self

    # --------------------------------------------------------
    # Drag start
    # --------------------------------------------------------

    def mouseDown_(self, event):

        self._drag_start = event.locationInWindow()

        self._start_origin = self.frame().origin

    # --------------------------------------------------------
    # Drag move
    # --------------------------------------------------------

    def mouseDragged_(self, event):

        if not hasattr(self, "_drag_start"):
            return

        current = event.locationInWindow()

        dx = current.x - self._drag_start.x
        dy = current.y - self._drag_start.y

        new_x = self._start_origin.x + dx
        new_y = self._start_origin.y + dy

        self.setFrameOrigin_((new_x, new_y))

    # --------------------------------------------------------
    # Progress update
    # --------------------------------------------------------

    def updateProgress_(self, percent):

        try:

            percent = max(
                0.0,
                min(100.0, float(percent))
            )

            # label
            try:

                if hasattr(self, "percent"):

                    self.percent.setStringValue_(
                        f"{int(percent)}%"
                    )

            except Exception:
                pass

            trackWidth = (
                self.progressTrack.bounds().size.width
            )

            newWidth = (
                trackWidth * (percent / 100.0)
            )

            frame = self.progressFill.frame()

            frame.size.width = newWidth

            # animation
            def animate(ctx):

                ctx.setDuration_(0.12)

                self.progressFill.animator().setFrame_(frame)

            NSAnimationContext.runAnimationGroup_completionHandler_(
                animate,
                None
            )

        except Exception as e:

            print(
                "[DownloadUI progress error]",
                e
            )

    # --------------------------------------------------------
    # Filename
    # --------------------------------------------------------

    def setFilename_(self, name):

        self.label.setStringValue_(name)

    # --------------------------------------------------------
    # Speed
    # --------------------------------------------------------

    def setSpeed_(self, speed):

        self.speed.setStringValue_(speed)

    # --------------------------------------------------------
    # Close
    # --------------------------------------------------------

    def closeDownload_(self, sender):

        try:

            self.setHidden_(True)

        except Exception as e:

            print(
                "[DownloadUI] close error:",
                e
            )
