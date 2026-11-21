"""Mobile (Android & iOS) personal-use UI refactor.

Targets:
- flutter/lib/mobile/pages/home_page.dart
- flutter/lib/mobile/pages/connection_page.dart
- flutter/lib/mobile/pages/server_page.dart
- flutter/lib/mobile/pages/settings_page.dart

Applies `better-*` parity:
- `>= 44x44px` touch targets with Semantics + Tooltip on Connect & Copy buttons
- `>= 16px` monospace tabular-nums inputs (prevents iOS zoom, removes digit ambiguity)
- Verified `RrColors` tokens across Light & Dark
- Strips Chat tab, 12s stranger scam countdown, One-time Password, MDM Deploy, unused 2FA
"""

from __future__ import annotations

from pathlib import Path

from . import read_text, replace_exact, write_text


def patch_mobile_ui(root: Path, update_repo: str) -> None:
    repo_url = f"https://github.com/{update_repo}"

    # ------------------------------------------------------------------
    # 1. mobile/pages/home_page.dart
    # ------------------------------------------------------------------
    home_p = root / "flutter" / "lib" / "mobile" / "pages" / "home_page.dart"
    htxt = read_text(home_p)
    htxt = replace_exact(
        htxt,
        """    if (isAndroid && !bind.isOutgoingOnly()) {
      _chatPageTabIndex = _pages.length;
      _pages.addAll([ChatPage(type: ChatPageType.mobileMain), ServerPage()]);
    }""",
        """    if (isAndroid && !bind.isOutgoingOnly()) {
      _chatPageTabIndex = -1;
      _pages.add(ServerPage());
    }""",
        "Remove redundant Chat tab from Android bottom navigation",
    )
    htxt = replace_exact(
        htxt,
        """          bottomNavigationBar: BottomNavigationBar(
            key: navigationBarKey,
            items: _pages
                .map((page) =>
                    BottomNavigationBarItem(icon: page.icon, label: page.title))
                .toList(),
            currentIndex: _selectedIndex,
            type: BottomNavigationBarType.fixed,
            selectedItemColor: MyTheme.accent, //
            unselectedItemColor: MyTheme.darkGray,""",
        """          bottomNavigationBar: Container(
            decoration: BoxDecoration(
              border: Border(
                top: BorderSide(
                  color: RrColors.of(context).borderSubtle,
                  width: 1,
                ),
              ),
            ),
            child: BottomNavigationBar(
            key: navigationBarKey,
            items: _pages
                .map((page) =>
                    BottomNavigationBarItem(icon: page.icon, label: page.title))
                .toList(),
            currentIndex: _selectedIndex,
            type: BottomNavigationBarType.fixed,
            selectedItemColor: RrColors.of(context).accentText,
            unselectedItemColor: RrColors.of(context).textSecondary,""",
        "Mobile BottomNavigationBar AA colors & borderSubtle divider (open)",
    )
    htxt = replace_exact(
        htxt,
        """            }),
          ),
          body: _pages.elementAt(_selectedIndex),""",
        """            }),
          ),
          ),
          body: _pages.elementAt(_selectedIndex),""",
        "Mobile BottomNavigationBar hairline divider (close)",
    )
    write_text(home_p, htxt)

    # ------------------------------------------------------------------
    # 2. mobile/pages/connection_page.dart
    # ------------------------------------------------------------------
    conn_p = root / "flutter" / "lib" / "mobile" / "pages" / "connection_page.dart"
    ctxt = read_text(conn_p)

    ctxt = replace_exact(
        ctxt,
        "final url = 'https://rustdesk.com/download';",
        f"final url = 'https://github.com/{update_repo}/releases/latest';",
        "Redirect mobile update URL to RRRemote repo",
    )
    ctxt = replace_exact(
        ctxt,
        """            child: Container(
                alignment: AlignmentDirectional.center,
                width: double.infinity,
                color: Colors.pinkAccent,
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(translate('Download new version'),
                    style: const TextStyle(
                        color: Colors.white, fontWeight: FontWeight.bold))));""",
        """            child: Container(
                alignment: AlignmentDirectional.center,
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 8),
                decoration: BoxDecoration(
                  color: RrColors.of(context).accentSolid,
                  borderRadius: BorderRadius.circular(10),
                ),
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Text(translate('Download new version'),
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.w600))));""",
        "Mobile update banner refined AA accent pill",
    )

    # Match platform in Mobile Quick-Connect autocomplete
    ctxt = replace_exact(
        ctxt,
        """                                peer.hostname
                                    .toLowerCase()
                                    .contains(textToFind) ||
                                peer.alias.toLowerCase().contains(textToFind))""",
        """                                peer.hostname
                                    .toLowerCase()
                                    .contains(textToFind) ||
                                peer.platform
                                    .toLowerCase()
                                    .contains(textToFind) ||
                                peer.alias.toLowerCase().contains(textToFind))""",
        "Include platform in Mobile Quick-Connect autocomplete",
    )

    ctxt = replace_exact(
        ctxt,
        """    final w = SizedBox(
      height: 84,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 2),
        child: Ink(
          decoration: BoxDecoration(
            color: Theme.of(context).cardColor,
            borderRadius: BorderRadius.all(Radius.circular(13)),
          ),""",
        """    final c = RrColors.of(context);
    final w = ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 72),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
        child: Ink(
          decoration: BoxDecoration(
            color: c.bgSurface,
            borderRadius: const BorderRadius.all(Radius.circular(14)),
            border: Border.all(
              color: c.borderControl,
              width: 1,
            ),
          ),""",
        "Responsive minHeight Mobile Quick-Connect bar with WCAG 1.4.11 border",
    )

    ctxt = replace_exact(
        ctxt,
        """                        minFontSize: 18,
                        autocorrect: false,
                        enableSuggestions: false,
                        keyboardType: TextInputType.visiblePassword,
                        // keyboardType: TextInputType.number,
                        onChanged: (String text) {
                          _idController.id = text;
                        },
                        style: const TextStyle(
                          fontFamily: 'WorkSans',
                          fontWeight: FontWeight.bold,
                          fontSize: 30,
                          color: MyTheme.idColor,
                        ),
                        decoration: InputDecoration(
                          labelText: translate('Remote ID'),
                          // hintText: 'Enter your remote ID',
                          border: InputBorder.none,
                          helperStyle: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                            color: MyTheme.darkGray,
                          ),
                          labelStyle: const TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 16,
                            letterSpacing: 0.2,
                            color: MyTheme.darkGray,
                          ),
                        ),""",
        """                        minFontSize: 16,
                        autocorrect: false,
                        enableSuggestions: false,
                        keyboardType: TextInputType.visiblePassword,
                        onChanged: (String text) {
                          _idController.id = text;
                        },
                        style: RrText.mono(
                          size: 20,
                          weight: FontWeight.w700,
                          color: c.textPrimary,
                          height: 1.25,
                        ),
                        decoration: InputDecoration(
                          labelText: translate('Remote ID'),
                          border: InputBorder.none,
                          helperStyle: TextStyle(
                            fontWeight: FontWeight.w500,
                            fontSize: 14,
                            color: c.textSecondary,
                          ),
                          labelStyle: TextStyle(
                            fontWeight: FontWeight.w600,
                            fontSize: 16,
                            color: c.textSecondary,
                          ),
                        ),""",
        "Mobile >=16px monospace tabular-nums Remote ID input",
    )

    ctxt = replace_exact(
        ctxt,
        """              SizedBox(
                width: 60,
                height: 60,
                child: IconButton(
                  icon: const Icon(Icons.arrow_forward,
                      color: MyTheme.darkGray, size: 45),
                  onPressed: onConnect,
                ),
              ),""",
        """              Padding(
                padding: const EdgeInsetsDirectional.only(end: 8),
                child: Semantics(
                  button: true,
                  label: translate('Connect'),
                  child: Tooltip(
                    message: translate('Connect'),
                    child: Material(
                      color: c.accentSolid,
                      borderRadius: BorderRadius.circular(8),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(8),
                        onTap: onConnect,
                        child: const SizedBox(
                          width: 44,
                          height: 44,
                          child: Icon(
                            Icons.arrow_forward_rounded,
                            color: Colors.white,
                            size: 22,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),""",
        "Accessible 44x44px Connect button on Mobile Quick-Connect bar",
    )
    write_text(conn_p, ctxt)

    # ------------------------------------------------------------------
    # 3. mobile/pages/server_page.dart
    # ------------------------------------------------------------------
    srv_p = root / "flutter" / "lib" / "mobile" / "pages" / "server_page.dart"
    stxt = read_text(srv_p)

    stxt = replace_exact(
        stxt,
        """                onPressed: () {
                  if (gFFI.userModel.userName.value.isEmpty &&
                      bind.mainGetLocalOption(key: "show-scam-warning") !=
                          "N") {
                    showScamWarning(context, serverModel);
                  } else {
                    serverModel.toggleService();
                  }
                },""",
        """                onPressed: () {
                  serverModel.toggleService();
                },""",
        "Bypass stranger scam countdown when starting Mobile screen share service",
    )
    stxt = replace_exact(
        stxt,
        """            PermissionRow(
                translate("Screen Capture"),
                serverModel.mediaOk,
                !serverModel.mediaOk &&
                        gFFI.userModel.userName.value.isEmpty &&
                        bind.mainGetLocalOption(key: "show-scam-warning") != "N"
                    ? () => showScamWarning(context, serverModel)
                    : serverModel.toggleService),""",
        """            PermissionRow(
                translate("Screen Capture"),
                serverModel.mediaOk,
                serverModel.toggleService),""",
        "Bypass stranger scam countdown on Mobile Screen Capture permission toggle",
    )
    stxt = replace_exact(
        stxt,
        """    final showOneTime = serverModel.approveMode != 'click' &&
        serverModel.verificationMethod != kUsePermanentPassword;
    return PaddingCard(
        title: translate('Your Device'),
        child: Column(
          // ID
          children: [
            Row(children: [
              const Icon(Icons.perm_identity,
                      color: Colors.grey, size: iconSize)
                  .marginOnly(right: iconMarginRight),
              Text(
                translate('ID'),
                style: textStyleHeading,
              )
            ]),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text(
                model.serverId.value.text,
                style: textStyleValue,
              ),
              IconButton(
                  visualDensity: VisualDensity.compact,
                  icon: Icon(Icons.copy_outlined),
                  onPressed: () {
                    copyToClipboard(model.serverId.value.text.trim());
                  })
            ]).marginOnly(left: 39, bottom: 10),
            // Password
            Row(children: [
              const Icon(Icons.lock_outline, color: Colors.grey, size: iconSize)
                  .marginOnly(right: iconMarginRight),
              Text(
                translate('One-time Password'),
                style: textStyleHeading,
              )
            ]),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Text(
                !showOneTime ? '-' : model.serverPasswd.value.text,
                style: textStyleValue,
              ),
              !showOneTime
                  ? SizedBox.shrink()
                  : Row(children: [
                      IconButton(
                          visualDensity: VisualDensity.compact,
                          icon: const Icon(Icons.refresh),
                          onPressed: () => bind.mainUpdateTemporaryPassword()),
                      IconButton(
                          visualDensity: VisualDensity.compact,
                          icon: Icon(Icons.copy_outlined),
                          onPressed: () {
                            copyToClipboard(
                                model.serverPasswd.value.text.trim());
                          })
                    ])
            ]).marginOnly(left: 40, bottom: 15),
            ConnectionStateNotification()
          ],
        ));""",
        """    final c = RrColors.of(context);
    return PaddingCard(
        title: translate('Your Device'),
        child: Column(
          children: [
            Row(children: [
              Icon(Icons.devices_rounded,
                      color: c.textSecondary, size: iconSize)
                  .marginOnly(right: iconMarginRight),
              Text(
                translate('ID'),
                style: textStyleHeading,
              )
            ]),
            Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              Expanded(
                child: SelectableText(
                  model.serverId.value.text,
                  style: RrText.mono(
                    size: 22.0,
                    weight: FontWeight.w700,
                    color: c.textPrimary,
                  ),
                ),
              ),
              Semantics(
                button: true,
                label: translate('Copy'),
                child: Tooltip(
                  message: translate('Copy'),
                  child: IconButton(
                      constraints:
                          const BoxConstraints(minWidth: 44, minHeight: 44),
                      icon: Icon(Icons.copy_rounded, color: c.accentText),
                      onPressed: () {
                        copyToClipboard(model.serverId.value.text.trim());
                      }),
                ),
              ),
            ]).marginOnly(left: 39, bottom: 12),
            const SizedBox(height: 8),
            ConnectionStateNotification()
          ],
        ));""",
        "Clean Mobile ServerInfo card with mono ID & 44x44px labeled Copy button",
    )
    stxt = replace_exact(
        stxt,
        "title: Text(translate('RustDesk storage')),",
        "title: Text(translate('RRRemote storage')),",
        "Rebrand Android file transfer workspace label",
    )
    stxt = replace_exact(
        stxt,
        "child: client.isFileTransfer || !client.authorized",
        "child: true",
        "Hide removed Chat tab shortcut in Mobile ConnectionManager",
    )
    write_text(srv_p, stxt)

    # ------------------------------------------------------------------
    # 4. mobile/pages/settings_page.dart
    # ------------------------------------------------------------------
    mset_p = root / "flutter" / "lib" / "mobile" / "pages" / "settings_page.dart"
    mstxt = read_text(mset_p)

    mstxt = replace_exact(
        mstxt,
        """                onPressed: (context) {
                  changeSocks5Proxy();
                }),
          if (isAndroid && !bind.isOutgoingOnly())
            SettingsTile(
                title: Text(translate('Deploy')),
                leading: Icon(Icons.cloud_upload),
                onPressed: (context) {
                  showDeployDialog();
                }),""",
        """                onPressed: (context) {
                  changeSocks5Proxy();
                }),
          // RRRemote personal edition: enterprise Deploy tile omitted""",
        "Hide enterprise MDM Deploy tile in Mobile Settings",
    )
    mstxt = replace_exact(
        mstxt,
        """        if (isAndroid &&
            !disabledSettings &&
            !outgoingOnly &&
            !hideSecuritySettings)
          SettingsSection(title: Text('2FA'), tiles: tfaTiles),""",
        """        if (isAndroid &&
            !disabledSettings &&
            !outgoingOnly &&
            !hideSecuritySettings &&
            enable2fa)
          SettingsSection(title: Text('2FA'), tiles: tfaTiles),""",
        "Hide unused 2FA section in Mobile Settings",
    )
    mstxt = replace_exact(
        mstxt,
        """            SettingsTile(
              title: Text(translate("Privacy Statement")),
              onPressed: (context) =>
                  launchUrlString('https://rustdesk.com/privacy.html'),
              leading: Icon(Icons.privacy_tip),
            )""",
        f"""            SettingsTile(
              title: const Text('GitHub repository'),
              onPressed: (context) => launchUrlString('{repo_url}'),
              leading: const Icon(Icons.code_rounded),
            )""",
        "Replace Privacy Statement tile with GitHub repository in Mobile About",
    )
    mstxt = (
        mstxt.replace("'https://rustdesk.com/'", f"'{repo_url}'")
        .replace("'https://rustdesk.com/privacy.html'", f"'{repo_url}'")
        .replace("Text('rustdesk.com'", "Text('RRRemote'")
        .replace("translate('About RustDesk')", "'About RRRemote'")
        .replace(
            "translate('Keep RustDesk background service')",
            "'Keep RRRemote background service'",
        )
    )
    write_text(mset_p, mstxt)
