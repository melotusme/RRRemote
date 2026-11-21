"""Desktop Settings decluttering (flutter/lib/desktop/pages/desktop_setting_page.dart).

- Streamlines sidebar to 5 personal tabs: General, Display, Network, Security, About.
- Hides unused 2FA card unless actively enabled.
- Removes Purslane Tech marketing banner & rustdesk.com commercial links; replaces
  with concise personal About card using RrColors semantic tokens.
"""

from __future__ import annotations

from pathlib import Path

from . import read_text, replace_exact, write_text


def patch_desktop_settings(root: Path, update_repo: str) -> None:
    p = root / "flutter" / "lib" / "desktop" / "pages" / "desktop_setting_page.dart"
    txt = read_text(p)
    repo_url = f"https://github.com/{update_repo}"

    # 1. Declutter Desktop Settings sidebar tabs: General, Display, Network, Security, About
    txt = replace_exact(
        txt,
        """  static final List<SettingsTabKey> tabKeys = [
    if (bind.mainGetBuildinOption(key: kOptionHideGeneralSetting) != 'Y')
      SettingsTabKey.general,
    if (!isWeb &&
        !bind.isOutgoingOnly() &&
        !bind.isDisableSettings() &&
        bind.mainGetBuildinOption(key: kOptionHideSecuritySetting) != 'Y')
      SettingsTabKey.safety,
    if (!bind.isDisableSettings() &&
        bind.mainGetBuildinOption(key: kOptionHideNetworkSetting) != 'Y')
      SettingsTabKey.network,
    if (!bind.isIncomingOnly()) SettingsTabKey.display,
    if (!bind.isDisableAccount()) SettingsTabKey.account,
    if (isWindows &&
        !bind.isDisableSettings() &&
        bind.mainGetBuildinOption(key: kOptionHideRemotePrinterSetting) != 'Y')
      SettingsTabKey.printer,
    SettingsTabKey.about,
  ];""",
        """  static final List<SettingsTabKey> tabKeys = [
    if (bind.mainGetBuildinOption(key: kOptionHideGeneralSetting) != 'Y')
      SettingsTabKey.general,
    if (!bind.isIncomingOnly()) SettingsTabKey.display,
    if (!bind.isDisableSettings() &&
        bind.mainGetBuildinOption(key: kOptionHideNetworkSetting) != 'Y')
      SettingsTabKey.network,
    if (!isWeb &&
        !bind.isOutgoingOnly() &&
        !bind.isDisableSettings() &&
        bind.mainGetBuildinOption(key: kOptionHideSecuritySetting) != 'Y')
      SettingsTabKey.safety,
    SettingsTabKey.about,
  ];""",
        "Declutter Desktop Settings sidebar to General, Display, Network, Security, About",
    )

    # 2. Hide unused 2FA card in Security tab unless actively set
    txt = replace_exact(
        txt,
        """                permissions(context),
                password(context),
                _Card(title: '2FA', children: [tfa()]),""",
        """                permissions(context),
                password(context),
                if (bind.mainHasValid2FaSync())
                  _Card(title: '2FA', children: [tfa()]),""",
        "Hide unused 2FA card in Desktop Security settings",
    )

    # 3. Clean Desktop About page (concise personal copy, no marketing fluff)
    txt = replace_exact(
        txt,
        """        child: _Card(title: translate('About RustDesk'), children: [""",
        """        child: _Card(title: 'RRRemote', children: [""",
        "Rename Desktop About card title to RRRemote",
    )
    txt = replace_exact(
        txt,
        """              InkWell(
                  onTap: () {
                    launchUrlString('https://rustdesk.com/privacy.html');
                  },
                  child: Text(
                    translate('Privacy Statement'),
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
              InkWell(
                  onTap: () {
                    launchUrlString('https://rustdesk.com');
                  },
                  child: Text(
                    translate('Website'),
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
              Container(
                decoration: const BoxDecoration(color: Color(0xFF2c8cff)),
                padding:
                    const EdgeInsets.symmetric(vertical: 24, horizontal: 8),
                child: SelectionArea(
                    child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Copyright © ${DateTime.now().toString().substring(0, 4)} Purslane Tech Pte. Ltd.\\n$license',
                            style: const TextStyle(color: Colors.white),
                          ),
                          Text(
                            translate('Slogan_tip'),
                            style: TextStyle(
                                fontWeight: FontWeight.w800,
                                color: Colors.white),
                          )
                        ],
                      ),
                    ),
                  ],
                )),
              ).marginSymmetric(vertical: 4.0)""",
        f"""              InkWell(
                  onTap: () {{
                    launchUrlString('{repo_url}');
                  }},
                  child: Text(
                    'Open GitHub repository ({update_repo})',
                    style: linkStyle,
                  ).marginSymmetric(vertical: 4.0)),
              Builder(
                builder: (ctx) {{
                  final c = RrColors.of(ctx);
                  return Container(
                    margin: const EdgeInsets.only(top: 8, bottom: 4),
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: c.bgSubtle,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: c.borderSubtle, width: 1),
                    ),
                    child: SelectionArea(
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              'RRRemote · Built on RustDesk 1.5.3\\n$license',
                              style: RrText.caption(
                                c.textSecondary,
                                weight: FontWeight.w400,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                }},
              )""",
        "Clean Desktop About page with concise copy & RrColors surface",
    )

    write_text(p, txt)
