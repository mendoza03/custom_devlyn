import { patch } from "@web/core/utils/patch";
import { WebClient } from "@web/webclient/webclient";
import { user } from "@web/core/user";

patch(WebClient.prototype, {
	/**
	* @override
	*/
	setup() {
		super.setup();
		this.user = user;
		// Update Favicons
		const favicon = `/web/image/res.company/${this.user.activeCompanies[0].id}/favicon`;
		const icons = document.querySelectorAll("link[rel*='icon']");
		for (const icon of icons) {
			if (icon.rel != 'apple-touch-icon')
				icon.href = favicon
		}
	}
});
