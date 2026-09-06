// Single source of truth for VS Code Webview API
let apiInstance: any = null;

export const getVsCodeApi = () => {
    if (!apiInstance) {
        try {
            // @ts-ignore
            if (typeof acquireVsCodeApi === 'function') {
                // @ts-ignore
                apiInstance = acquireVsCodeApi();
            }
        } catch (e) {
            // In case acquireVsCodeApi was already called elsewhere or in window scope
            // @ts-ignore
            apiInstance = window.vscode || null;
        }
    }
    return apiInstance;
};

export const postVsCodeMessage = (message: any) => {
    const api = getVsCodeApi();
    if (api) {
        api.postMessage(message);
    } else {
        console.log('[Webview mock postMessage]', message);
    }
};
