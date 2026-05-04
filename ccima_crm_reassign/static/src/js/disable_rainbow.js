/** @odoo-module **/

function startRainbowNuker() {
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (
                    node.nodeType === 1 &&
                    node.classList.contains("o_reward")
                ) {
                    node.remove();
                }
            }
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startRainbowNuker);
} else {
    startRainbowNuker();
}
