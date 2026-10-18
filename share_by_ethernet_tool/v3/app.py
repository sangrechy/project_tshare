"""
T-Share v3 Desktop Application Entrypoint
Launches PyWebView with high-performance native rendering and decoupled bridge API.
"""

import os
import sys
import webview
from backend.bridge import BridgeAPI


def main():
    # Resolve absolute paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ui_dir = os.path.join(base_dir, "ui")
    index_html = os.path.join(ui_dir, "index.html")

    if not os.path.exists(index_html):
        print(f"Error: UI file not found: {index_html}", file=sys.stderr)
        sys.exit(1)

    # Initialize Decoupled JavaScript Bridge
    bridge = BridgeAPI()

    # Create PyWebView Native Window
    window = webview.create_window(
        title="T-Share v3 — Direct Ethernet High-Speed Transfer",
        url=f"file://{index_html}",
        js_api=bridge,
        width=1120,
        height=760,
        min_size=(900, 620),
        background_color="#0b0f19"
    )

    bridge.set_window(window)

    def on_loaded():
        bridge.start_background_services()

    def on_closed():
        bridge.stop_background_services()

    window.events.loaded += on_loaded
    window.events.closed += on_closed

    # Start PyWebView GUI loop
    webview.start(debug=False)


if __name__ == "__main__":
    main()
