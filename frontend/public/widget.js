/**
 * ==============================================================================
 * College AI Help Desk — Embeddable Chatbot Widget Loader
 * ==============================================================================
 * Lightweight, zero-dependency embedding script.
 * Isolates CSS and JavaScript using a secure iframe layer.
 * 
 * Usage:
 * <script
 *   src="http://127.0.0.1:5175/widget.js"
 *   data-chatbot-id="college-helpdesk"
 *   data-api-base="http://127.0.0.1:8005"
 *   data-position="bottom-right"
 *   defer
 * ></script>
 */
(function () {
  'use strict';

  if (window.__CollegeHelpdeskInitialized) {
    return;
  }
  window.__CollegeHelpdeskInitialized = true;

  // 1. Locate current script element and extract configuration
  const currentScript =
    document.currentScript ||
    document.querySelector('script[data-chatbot-id]') ||
    document.querySelector('script[src*="widget.js"]');

  const scriptSrc = currentScript ? currentScript.src : window.location.origin;
  const scriptOrigin = new URL(scriptSrc, window.location.href).origin;

  const chatbotId = currentScript?.getAttribute('data-chatbot-id') || 'college-helpdesk';
  const apiBase = currentScript?.getAttribute('data-api-base') || scriptOrigin;
  const position = currentScript?.getAttribute('data-position') || 'bottom-right';
  const primaryColor = currentScript?.getAttribute('data-primary-color') || '#1e3a8a';
  const customWidgetUrl = currentScript?.getAttribute('data-widget-url');

  // Compute full widget iframe URL
  const widgetUrl = new URL(customWidgetUrl || `${scriptOrigin}/widget`);
  widgetUrl.searchParams.set('botId', chatbotId);
  widgetUrl.searchParams.set('apiBase', encodeURIComponent(apiBase));
  widgetUrl.searchParams.set('position', position);
  if (primaryColor) {
    widgetUrl.searchParams.set('primaryColor', encodeURIComponent(primaryColor));
  }

  // 2. Create host container wrapper
  const container = document.createElement('div');
  container.id = 'college-helpdesk-widget-container';
  container.setAttribute('aria-hidden', 'false');

  const isLeft = position === 'bottom-left';

  // Base closed dimensions
  const CLOSED_WIDTH = '90px';
  const CLOSED_HEIGHT = '90px';
  const OPEN_DESKTOP_WIDTH = '440px';
  const OPEN_DESKTOP_HEIGHT = '700px';

  function applyContainerStyles(isOpen) {
    const isMobile = window.innerWidth <= 640;

    container.style.position = 'fixed';
    container.style.zIndex = '2147483647';
    container.style.border = 'none';
    container.style.background = 'transparent';
    container.style.pointerEvents = 'none'; // container itself doesn't block clicks; iframe inside has pointer-events: auto
    container.style.transition = 'width 0.2s ease, height 0.2s ease';

    if (isOpen) {
      if (isMobile) {
        container.style.top = '0px';
        container.style.left = '0px';
        container.style.right = '0px';
        container.style.bottom = '0px';
        container.style.width = '100vw';
        container.style.height = '100vh';
        container.style.maxWidth = '100%';
        container.style.maxHeight = '100%';
      } else {
        container.style.top = 'auto';
        container.style.bottom = '0px';
        if (isLeft) {
          container.style.left = '0px';
          container.style.right = 'auto';
        } else {
          container.style.right = '0px';
          container.style.left = 'auto';
        }
        container.style.width = OPEN_DESKTOP_WIDTH;
        container.style.height = OPEN_DESKTOP_HEIGHT;
        container.style.maxWidth = '96vw';
        container.style.maxHeight = '96vh';
      }
    } else {
      container.style.top = 'auto';
      container.style.bottom = '0px';
      if (isLeft) {
        container.style.left = '0px';
        container.style.right = 'auto';
      } else {
        container.style.right = '0px';
        container.style.left = 'auto';
      }
      container.style.width = CLOSED_WIDTH;
      container.style.height = CLOSED_HEIGHT;
      container.style.maxWidth = CLOSED_WIDTH;
      container.style.maxHeight = CLOSED_HEIGHT;
    }
  }

  applyContainerStyles(false);

  // 3. Create isolated iframe
  const iframe = document.createElement('iframe');
  iframe.id = 'college-helpdesk-iframe';
  iframe.title = 'College AI Help Desk Virtual Assistant';
  iframe.src = widgetUrl.href;
  iframe.setAttribute('allow', 'clipboard-write');
  iframe.style.width = '100%';
  iframe.style.height = '100%';
  iframe.style.border = 'none';
  iframe.style.background = 'transparent';
  iframe.style.overflow = 'hidden';
  iframe.style.pointerEvents = 'auto'; // allow clicks inside the iframe

  container.appendChild(iframe);

  // 4. Attach to DOM once body is ready
  function attachWidget() {
    if (document.body) {
      document.body.appendChild(container);
    } else {
      document.addEventListener('DOMContentLoaded', () => document.body.appendChild(container));
    }
  }
  attachWidget();

  // 5. PostMessage synchronization between host and widget iframe
  let isWidgetOpen = false;

  window.addEventListener('message', function (event) {
    // Only accept messages from the widget iframe origin
    if (event.origin !== scriptOrigin && event.origin !== window.location.origin) {
      return;
    }

    const data = event.data;
    if (!data || typeof data !== 'object') return;

    switch (data.type) {
      case 'helpdesk:open':
        isWidgetOpen = true;
        applyContainerStyles(true);
        break;

      case 'helpdesk:close':
        isWidgetOpen = false;
        applyContainerStyles(false);
        break;

      case 'helpdesk:resize':
        if (data.width && data.height && !isWidgetOpen) {
          container.style.width = data.width;
          container.style.height = data.height;
        }
        break;

      case 'helpdesk:ready':
        // Acknowledge and transmit host origin for security validation
        iframe.contentWindow?.postMessage(
          {
            type: 'helpdesk:init',
            hostOrigin: window.location.origin,
            chatbotId: chatbotId,
          },
          '*'
        );
        break;
    }
  });

  // Handle window resizing (mobile rotation or resize)
  window.addEventListener('resize', function () {
    if (isWidgetOpen) {
      applyContainerStyles(true);
    }
  });

  // 6. Expose global control API for the host website
  window.CollegeHelpdesk = {
    open: function () {
      isWidgetOpen = true;
      applyContainerStyles(true);
      iframe.contentWindow?.postMessage({ type: 'helpdesk:command:open' }, '*');
    },
    close: function () {
      isWidgetOpen = false;
      applyContainerStyles(false);
      iframe.contentWindow?.postMessage({ type: 'helpdesk:command:close' }, '*');
    },
    toggle: function () {
      if (isWidgetOpen) {
        this.close();
      } else {
        this.open();
      }
    },
    isLoaded: true,
    version: '0.1.0',
  };

  console.log('College AI Help Desk Widget Loader initialized successfully.');
})();
