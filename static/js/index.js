document.addEventListener('DOMContentLoaded', async function () {
	const sel = document.getElementById('theme-selector');
	if (!sel) return;

	let themes = [];
	try {
		const resp = await fetch('/api/themes');
		themes = await resp.json();
		if (themes && themes.themes) {
			themes.themes.forEach(function (t) {
				const opt = document.createElement('option');
				opt.value = t.name;
				opt.dataset.light = t.light_css_file;
				opt.dataset.dark = t.dark_css_file;
				opt.textContent = t.name;
				sel.appendChild(opt);
			});

			// try to select current theme by comparing stylesheet href
			const currentHref = (document.getElementById('theme-stylesheet') || {}).href || window.currentThemeURL || '';
			let matched = false;
			for (let i = 0; i < sel.options.length; i++) {
				const o = sel.options[i];
				if ((o.dataset.light && o.dataset.light === currentHref) || (o.dataset.dark && o.dataset.dark === currentHref)) {
					sel.selectedIndex = i;
					matched = true;
					break;
				}
			}

			// if none matched, pick the active theme from API
			if (!matched) {
				for (let i = 0; i < themes.themes.length; i++) {
					if (themes.themes[i].active) {
						sel.selectedIndex = i;
						break;
					}
				}
			}
		}
	} catch (e) {
		console.error('Failed to load themes', e);
	}

	const darkToggle = document.getElementById('dark-mode-toggle');

	function applyTheme() {
		const selected = sel.options[sel.selectedIndex];
		if (!selected) return;
		const css = (darkToggle && darkToggle.checked) ? selected.dataset.dark : selected.dataset.light;
		if (!css) return;
		const link = document.getElementById('theme-stylesheet');
		if (link) link.href = css;

		if (window.isLoggedIn) {
			// save to profile: send url, theme name and mode
			const payload = {
				theme_url: css,
				theme: selected.value,
				mode: (darkToggle && darkToggle.checked) ? 'dark' : 'light',
				dark_mode: !!(darkToggle && darkToggle.checked)
			};
			fetch('/account/theme', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			}).catch(console.error);
		} else {
			// save as cookie for 1 year
			const d = new Date(); d.setTime(d.getTime() + (365 * 24 * 60 * 60 * 1000));
			document.cookie = 'mbt_theme=' + encodeURIComponent(css) + ';path=/;expires=' + d.toUTCString();
		}
	}

	sel.addEventListener('change', applyTheme);
	if (darkToggle) darkToggle.addEventListener('change', applyTheme);
});
