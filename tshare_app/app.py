"""
T-Share Unified Desktop Application Entrypoint
Launches PyWebView native window with high-performance desktop rendering.
Automatically falls back to local Web Browser Mode if native WebKit/GTK/Qt is not present.
"""

import os
import sys
import webbrowser
from backend.bridge import BridgeAPI


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ui_dir = os.path.join(base_dir, "ui")
    index_html = os.path.join(ui_dir, "index.html")

    if not os.path.exists(index_html):
        print(f"Error: UI file not found: {index_html}", file=sys.stderr)
        sys.exit(1)

    # Initialize Decoupled JavaScript Bridge
    bridge = BridgeAPI(ui_dir=ui_dir)

    force_browser = "--browser" in sys.argv or "--web" in sys.argv

    if not force_browser:
        try:
            import webview

            window = webview.create_window(
                title="T-Share — Unified High-Speed Wire & Web Sharing Suite",
                url=f"file://{index_html}",
                js_api=bridge,
                width=1160,
                height=780,
                min_size=(920, 640),
                background_color="#0b0f19"
            )

            bridge.set_window(window)

            def on_loaded():
                bridge.start_background_services()

            def on_closed():
                bridge.stop_background_services()

            window.events.loaded += on_loaded
            window.events.closed += on_closed

            webview.start(debug=False)
            return
        except Exception as e:
            print(f"\n[!] Native desktop window engine not available ({e}).")
            print("[*] Automatically switching to high-speed Browser Mode...\n")

    # Seamless Fallback: Built-in Browser Mode
    bridge.set_window(None)
    bridge.start_background_services()

    portal_status = bridge.get_web_portal_status()
    port = portal_status["port"]
    url = f"http://127.0.0.1:{port}"

    print(f"\n========================================================")
    print(f"  [T-SHARE UNIFIED WEB MODE] Running at: {url}")
    print(f"  LAN Smartphone/Browser Portal at:      {url}/portal")
    print(f"  Opening default system browser...")
    print(f"  Press Ctrl+C to exit.")
    print(f"========================================================\n")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    try:
        import time
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        bridge.stop_background_services()


if __name__ == "__main__":
    main()
