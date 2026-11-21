"""Desktop Home Page refactor (flutter/lib/desktop/pages/desktop_home_page.dart).

Applies all 7 `better-*` skills:
- `better-layout`: Responsive 240px sidebar collapsing to compact top strip < 720px;
  shared 16px alignment edges; logical EdgeInsetsDirectional; no decorative inner Divider.
- `better-accessibility`: CallbackShortcuts (Cmd/Ctrl+K, Cmd/Ctrl+1/2/3, Cmd/Ctrl+,),
  >= 32x32px icon buttons with Semantics + Tooltip, non-color-only status icons + text,
  manual Update banner (no unsolicited background auto-download).
- `better-colors`: RrColors semantic warning (amber) for macOS TCC permissions,
  danger (red) for stopped service / unreachable server, accentSoft for updates.
- `better-typography`: Monospace tabular-nums + slashed-zero Device ID (20px w700),
  strict 12/14/16/20px scale.
- `better-writing`: Unified macOS TCC checklist naming all missing permissions +
  quit/reopen instruction; actionable service/server recovery CTAs.
"""

from __future__ import annotations

from pathlib import Path

from . import read_text, replace_exact, write_text


def patch_desktop_home_page(root: Path, update_repo: str) -> None:
    p = root / "flutter" / "lib" / "desktop" / "pages" / "desktop_home_page.dart"
    txt = read_text(p)

    # 1. Add copied feedback flag for This Device ID card
    txt = replace_exact(
        txt,
        """  Timer? _updateTimer;
  bool isCardClosed = false;""",
        """  Timer? _updateTimer;
  bool isCardClosed = false;
  final RxBool _idCopied = false.obs;""",
        "Add _idCopied visual feedback state in DesktopHomePage",
    )

    # 2. Wrap DesktopHomePage.build with CallbackShortcuts + responsive LayoutBuilder (<720px collapse)
    txt = replace_exact(
        txt,
        """  @override
  Widget build(BuildContext context) {
    super.build(context);
    final isIncomingOnly = bind.isIncomingOnly();
    return _buildBlock(
        child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        buildLeftPane(context),
        if (!isIncomingOnly) const VerticalDivider(width: 1),
        if (!isIncomingOnly) Expanded(child: buildRightPane(context)),
      ],
    ));
  }""",
        """  void _focusQuickConnect() {
    if (Get.isRegistered<FocusNode>(tag: 'rr-quick-connect-focus')) {
      Get.find<FocusNode>(tag: 'rr-quick-connect-focus').requestFocus();
    }
  }

  void _switchPeerTab(int tabIndex) {
    final visible = gFFI.peerTabModel.visibleEnabledOrderedIndexs;
    if (visible.contains(tabIndex)) {
      gFFI.peerTabModel.setCurrentTab(tabIndex);
      bind.setLocalFlutterOption(k: kOptionPeerTabIndex, v: tabIndex.toString());
    }
  }

  void _copyThisDeviceId() {
    final idText = gFFI.serverModel.serverId.text.trim();
    if (idText.isEmpty) return;
    Clipboard.setData(ClipboardData(text: idText));
    showToast(translate("Copied"));
    _idCopied.value = true;
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) _idCopied.value = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final isIncomingOnly = bind.isIncomingOnly();
    final c = RrColors.of(context);
    final shortcuts = <ShortcutActivator, VoidCallback>{
      SingleActivator(LogicalKeyboardKey.keyK, meta: isMacOS, control: !isMacOS):
          _focusQuickConnect,
      SingleActivator(LogicalKeyboardKey.comma,
              meta: isMacOS, control: !isMacOS):
          DesktopTabPage.onAddSetting,
      SingleActivator(LogicalKeyboardKey.digit1,
          meta: isMacOS, control: !isMacOS): () => _switchPeerTab(1),
      SingleActivator(LogicalKeyboardKey.digit2,
          meta: isMacOS, control: !isMacOS): () => _switchPeerTab(0),
      SingleActivator(LogicalKeyboardKey.digit3,
          meta: isMacOS, control: !isMacOS): () => _switchPeerTab(2),
    };
    return CallbackShortcuts(
      bindings: shortcuts,
      child: _buildBlock(
        child: isIncomingOnly
            ? buildLeftPane(context)
            : LayoutBuilder(
                builder: (context, constraints) {
                  final compact = constraints.maxWidth < 720;
                  if (compact) {
                    return Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _buildCompactTopStrip(context),
                        Divider(height: 1, thickness: 1, color: c.borderSubtle),
                        Expanded(child: buildRightPane(context)),
                      ],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      buildLeftPane(context),
                      VerticalDivider(
                          width: 1, thickness: 1, color: c.borderSubtle),
                      Expanded(child: buildRightPane(context)),
                    ],
                  );
                },
              ),
      ),
    );
  }

  Widget _buildCompactTopStrip(BuildContext context) {
    final c = RrColors.of(context);
    final model = gFFI.serverModel;
    final isOutgoingOnly = bind.isOutgoingOnly();
    return ChangeNotifierProvider.value(
      value: model,
      child: Container(
        color: c.bgCanvas,
        padding: const EdgeInsetsDirectional.fromSTEB(16, 10, 12, 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                loadLogo(),
                const SizedBox(width: 12),
                if (!isOutgoingOnly)
                  Expanded(
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Flexible(
                          child: ValueListenableBuilder<TextEditingValue>(
                            valueListenable: model.serverId,
                            builder: (_, val, __) => SelectableText(
                              val.text,
                              maxLines: 1,
                              style: RrText.mono(
                                size: 15,
                                weight: FontWeight.w700,
                                color: c.textPrimary,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        _buildCopyIdButton(context),
                      ],
                    ),
                  )
                else
                  const Spacer(),
                buildPopupMenu(context),
              ],
            ),
            Obx(() => buildHelpCards(stateGlobal.updateUrl.value)),
          ],
        ),
      ),
    );
  }""",
        "Add CallbackShortcuts and responsive <720px sidebar collapse in DesktopHomePage",
    )

    # 3. Clean left host pane: remove Powered-by, stranger tip, and One-time Password; 240px width
    txt = replace_exact(
        txt,
        """      if (bind.isCustomClient())
        Align(
          alignment: Alignment.center,
          child: loadPowered(context),
        ),
      Align(
        alignment: Alignment.center,
        child: loadLogo(),
      ),
      buildTip(context),
      if (!isOutgoingOnly) buildIDBoard(context),
      if (!isOutgoingOnly) buildPasswordBoard(context),""",
        """      Padding(
        padding: const EdgeInsetsDirectional.fromSTEB(16, 16, 12, 8),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            loadLogo(),
            buildPopupMenu(context),
          ],
        ),
      ),
      if (!isOutgoingOnly) buildIDBoard(context),""",
        "Clean sidebar header with shared 16px edge and remove tip/password/watermark",
    )

    txt = replace_exact(
        txt,
        """      child: Container(
        width: isIncomingOnly ? 280.0 : 200.0,
        color: Theme.of(context).colorScheme.background,""",
        """      child: Container(
        width: isIncomingOnly ? 288.0 : 240.0,
        color: RrColors.of(context).bgCanvas,""",
        "Set left host sidebar width to 240px and bgCanvas surface",
    )

    # 4. Refactor buildIDBoard & buildPopupMenu with accessible >=32px targets, mono ID,
    #    and full-width clickable Health & Server Status row (never color alone!)
    txt = replace_exact(
        txt,
        """  buildIDBoard(BuildContext context) {
    final model = gFFI.serverModel;
    return Container(
      margin: const EdgeInsets.only(left: 20, right: 11),
      height: 57,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.baseline,
        textBaseline: TextBaseline.alphabetic,
        children: [
          Container(
            width: 2,
            decoration: const BoxDecoration(color: MyTheme.accent),
          ).marginOnly(top: 5),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(left: 7),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    height: 25,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          translate("ID"),
                          style: TextStyle(
                              fontSize: 14,
                              color: Theme.of(context)
                                  .textTheme
                                  .titleLarge
                                  ?.color
                                  ?.withOpacity(0.5)),
                        ).marginOnly(top: 5),
                        buildPopupMenu(context)
                      ],
                    ),
                  ),
                  Flexible(
                    child: GestureDetector(
                      onDoubleTap: () {
                        Clipboard.setData(
                            ClipboardData(text: model.serverId.text));
                        showToast(translate("Copied"));
                      },
                      child: TextFormField(
                        controller: model.serverId,
                        readOnly: true,
                        decoration: InputDecoration(
                          border: InputBorder.none,
                          contentPadding: EdgeInsets.only(top: 10, bottom: 10),
                        ),
                        style: TextStyle(
                          fontSize: 22,
                        ),
                      ).workaroundFreezeLinuxMint(),
                    ),
                  )
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildPopupMenu(BuildContext context) {
    final textColor = Theme.of(context).textTheme.titleLarge?.color;
    RxBool hover = false.obs;
    return InkWell(
      onTap: DesktopTabPage.onAddSetting,
      child: Tooltip(
        message: translate('Settings'),
        child: Obx(
          () => CircleAvatar(
            radius: 15,
            backgroundColor: hover.value
                ? Theme.of(context).scaffoldBackgroundColor
                : Theme.of(context).colorScheme.background,
            child: Icon(
              Icons.more_vert_outlined,
              size: 20,
              color: hover.value ? textColor : textColor?.withOpacity(0.5),
            ),
          ),
        ),
      ),
      onHover: (value) => hover.value = value,
    );
  }""",
        """  Widget _buildCopyIdButton(BuildContext context) {
    final c = RrColors.of(context);
    return Semantics(
      button: true,
      label: translate('Copy'),
      child: Tooltip(
        message: translate('Copy'),
        child: Obx(() {
          final copied = _idCopied.value;
          return Material(
            color: copied ? c.successSoft : c.accentSoft,
            borderRadius: BorderRadius.circular(8),
            child: InkWell(
              borderRadius: BorderRadius.circular(8),
              onTap: _copyThisDeviceId,
              child: SizedBox(
                width: 32,
                height: 32,
                child: Icon(
                  copied ? Icons.check_rounded : Icons.copy_rounded,
                  size: 16,
                  color: copied ? c.successText : c.accentText,
                ),
              ),
            ),
          );
        }),
      ),
    );
  }

  buildIDBoard(BuildContext context) {
    final model = gFFI.serverModel;
    final c = RrColors.of(context);
    return Container(
      margin: const EdgeInsetsDirectional.fromSTEB(16, 8, 16, 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: c.bgSurface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: c.borderSubtle, width: 1),
        boxShadow: c.cardElevation(context),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            translate("ID"),
            style: RrText.caption(c.textSecondary, weight: FontWeight.w600),
          ),
          const SizedBox(height: 6),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: ValueListenableBuilder<TextEditingValue>(
                  valueListenable: model.serverId,
                  builder: (_, val, __) => GestureDetector(
                    onDoubleTap: _copyThisDeviceId,
                    child: SelectableText(
                      val.text.isEmpty ? '—' : val.text,
                      maxLines: 1,
                      style: RrText.mono(
                        size: 20,
                        weight: FontWeight.w700,
                        color: c.textPrimary,
                        letterSpacing: 0.4,
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              _buildCopyIdButton(context),
            ],
          ),
          const SizedBox(height: 12),
          Obx(() {
            final stopped = svcStopped.value;
            final status = stateGlobal.svcStatus.value;
            final isReady = !stopped && status == SvcStatus.ready;
            final isConnecting = !stopped && status == SvcStatus.connecting;
            final IconData statusIcon = stopped
                ? Icons.pause_circle_rounded
                : isConnecting
                    ? Icons.sync_rounded
                    : isReady
                        ? Icons.check_circle_rounded
                        : Icons.error_rounded;
            final Color badgeBg = stopped
                ? c.dangerSoft
                : isConnecting
                    ? c.warningSoft
                    : isReady
                        ? c.successSoft
                        : c.dangerSoft;
            final Color badgeFg = stopped
                ? c.dangerText
                : isConnecting
                    ? c.warningText
                    : isReady
                        ? c.successText
                        : c.dangerText;
            final String statusLabel = stopped
                ? translate("Service is not running")
                : isConnecting
                    ? translate("connecting_status")
                    : isReady
                        ? translate("Ready")
                        : 'Server unreachable';
            final canOpenSettings = !bind.isDisableSettings();
            return Semantics(
              button: canOpenSettings,
              label: '$statusLabel. ${translate('ID/Relay Server')}',
              child: Tooltip(
                message: canOpenSettings
                    ? translate('ID/Relay Server')
                    : statusLabel,
                child: Material(
                  color: badgeBg,
                  borderRadius: BorderRadius.circular(8),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(8),
                    onTap: canOpenSettings
                        ? () => DesktopSettingPage.switch2page(
                            SettingsTabKey.network)
                        : null,
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: 36),
                      child: Padding(
                        padding: const EdgeInsetsDirectional.fromSTEB(
                            10, 6, 8, 6),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            Icon(statusIcon, size: 16, color: badgeFg),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                statusLabel,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: RrText.caption(
                                  badgeFg,
                                  weight: FontWeight.w600,
                                ),
                              ),
                            ),
                            if (canOpenSettings)
                              Icon(
                                Icons.chevron_right_rounded,
                                size: 16,
                                color: badgeFg,
                              ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget buildPopupMenu(BuildContext context) {
    final c = RrColors.of(context);
    final shortcutHint = isMacOS ? '⌘,' : 'Ctrl+,';
    return Semantics(
      button: true,
      label: translate('Settings'),
      child: Tooltip(
        message: '${translate('Settings')} ($shortcutHint)',
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          child: InkWell(
            borderRadius: BorderRadius.circular(8),
            hoverColor: c.bgHover,
            onTap: DesktopTabPage.onAddSetting,
            child: SizedBox(
              width: 34,
              height: 34,
              child: Icon(
                Icons.tune_rounded,
                size: 18,
                color: c.textSecondary,
              ),
            ),
          ),
        ),
      ),
    );
  }""",
        "Accessible This Device ID card with 32px Copy & 36px Health/Server row",
    )

    # 5. Update card + priority ordering: macOS TCC permissions & stopped service/daemon
    #    ALWAYS render ABOVE any Update banner so updates never hide missing input permissions.
    txt = replace_exact(
        txt,
        """    if (!bind.isCustomClient() &&
        updateUrl.isNotEmpty &&
        !isCardClosed &&
        bind.mainUriPrefixSync().contains('rustdesk')) {
      final isToUpdate = (isWindows || isMacOS) && bind.mainIsInstalled();
      String btnText = isToUpdate ? 'Update' : 'Download';
      GestureTapCallback onPressed = () async {
        final Uri url = Uri.parse('https://rustdesk.com/download');
        await launchUrl(url);
      };
      if (isToUpdate) {
        onPressed = () {
          handleUpdate(updateUrl);
        };
      }
      return buildInstallCard(
          "Status",
          "${translate("new-version-of-{${bind.mainGetAppNameSync()}}-tip")} (${bind.mainGetNewVersion()}).",
          btnText,
          onPressed,
          closeButton: true,
          help: isToUpdate ? 'Changelog' : null,
          link: isToUpdate
              ? 'https://github.com/rustdesk/rustdesk/releases/tag/${bind.mainGetNewVersion()}'
              : null);
    }""",
        f"""    Widget? updateBanner;
    if (updateUrl.isNotEmpty &&
        !isCardClosed &&
        (bind.mainUriPrefixSync().contains('rustdesk') ||
            bind.mainUriPrefixSync().contains('rrremote'))) {{
      final isToUpdate = (isWindows || isMacOS) && bind.mainIsInstalled();
      final btnText = isToUpdate ? 'Install update' : 'Download update';
      GestureTapCallback onPressed = () async {{
        final Uri url = Uri.parse('https://github.com/{update_repo}/releases/latest');
        await launchUrl(url);
      }};
      if (isToUpdate) {{
        onPressed = () {{
          handleUpdate(updateUrl);
        }};
      }}
      final newVer = bind.mainGetNewVersion();
      updateBanner = buildInstallCard(
          'Update available',
          'RRRemote $newVer is ready to install.',
          btnText,
          onPressed,
          closeButton: true,
          tone: 'info',
          help: isToUpdate ? 'View release notes' : null,
          link: isToUpdate
              ? 'https://github.com/{update_repo}/releases/tag/$newVer'
              : null);
    }}
    Widget withUpdate(Widget primary) {{
      if (updateBanner == null) return primary;
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [primary, updateBanner],
      );
    }}
    if (isMacOS) {{
      final isOutgoingOnly = bind.isOutgoingOnly();
      final missingScreen =
          !(isOutgoingOnly || bind.mainIsCanScreenRecording(prompt: false));
      final missingAcc =
          !isOutgoingOnly && !bind.mainIsProcessTrusted(prompt: false);
      final missingInput = !bind.mainIsCanInputMonitoring(prompt: false);
      if (missingScreen || missingAcc || missingInput) {{
        return withUpdate(_buildMacTccChecklistCard(
          context,
          missingScreen: missingScreen,
          missingAcc: missingAcc,
          missingInput: missingInput,
        ));
      }} else if (!isOutgoingOnly && svcStopped.value) {{
        return withUpdate(buildInstallCard(
          'Background service stopped',
          'Start the service so your other devices can reach this Mac.',
          'Start service',
          () async {{
            await start_service(true);
          }},
          tone: 'danger',
        ));
      }} else if (!isOutgoingOnly &&
          !svcStopped.value &&
          bind.mainIsInstalled() &&
          !bind.mainIsInstalledDaemon(prompt: false)) {{
        return withUpdate(buildInstallCard(
          'Background daemon needed',
          'Install the macOS service for unattended access and login screen control.',
          'Install service',
          () async {{
            bind.mainIsInstalledDaemon(prompt: true);
          }},
          tone: 'danger',
        ));
      }} else if (!isOutgoingOnly &&
          stateGlobal.svcStatus.value == SvcStatus.notReady &&
          !bind.isDisableSettings()) {{
        return withUpdate(buildInstallCard(
          'Server unreachable',
          'Check your relay server address or network connection.',
          'Open server settings',
          () {{
            DesktopSettingPage.switch2page(SettingsTabKey.network);
          }},
          tone: 'danger',
        ));
      }}
    }}
    if (!isMacOS && !bind.isOutgoingOnly() && svcStopped.value) {{
      return withUpdate(buildInstallCard(
        'Background service stopped',
        'Start the service so your other devices can reach this machine.',
        'Start service',
        () async {{
          await start_service(true);
        }},
        tone: 'danger',
      ));
    }}
    if (updateBanner != null) {{
      return updateBanner;
    }}""",
        "Prioritize macOS TCC permissions & service recovery above Update banner",
    )

    # 6. Remove now-superseded lower macOS branch (handled above before Update banner)
    txt = replace_exact(
        txt,
        """    } else if (isMacOS) {
      final isOutgoingOnly = bind.isOutgoingOnly();
      if (!(isOutgoingOnly || bind.mainIsCanScreenRecording(prompt: false))) {
        return buildInstallCard("Permissions", "config_screen", "Configure",
            () async {
          bind.mainIsCanScreenRecording(prompt: true);
          // macOS shows the request prompt only once per app, so later
          // presses would do nothing without opening the settings pane.
          launchUrl(Uri.parse(
              'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'));
          watchIsCanScreenRecording = true;
        }, help: 'Help', link: translate("doc_mac_permission"));
      } else if (!isOutgoingOnly && !bind.mainIsProcessTrusted(prompt: false)) {
        return buildInstallCard("Permissions", "config_acc", "Configure",
            () async {
          bind.mainIsProcessTrusted(prompt: true);
          watchIsProcessTrust = true;
        }, help: 'Help', link: translate("doc_mac_permission"));
      } else if (!bind.mainIsCanInputMonitoring(prompt: false)) {
        return buildInstallCard("Permissions", "config_input", "Configure",
            () async {
          bind.mainIsCanInputMonitoring(prompt: true);
          watchIsInputMonitoring = true;
        }, help: 'Help', link: translate("doc_mac_permission"));
      } else if (!isOutgoingOnly &&
          !svcStopped.value &&
          bind.mainIsInstalled() &&
          !bind.mainIsInstalledDaemon(prompt: false)) {
        return buildInstallCard("", "install_daemon_tip", "Install", () async {
          bind.mainIsInstalledDaemon(prompt: true);
        });
      }""",
        """    } else if (isMacOS) {
      // Handled with priority above Update banner so missing TCC/service cards are never hidden.""",
        "Deduplicate macOS branch after moving above Update banner",
    )

    # Also add desktop server-unreachable recovery fallback for non-macOS before final return Container()
    txt = replace_exact(
        txt,
        """    if (bind.isIncomingOnly()) {""",
        """    if (!isMacOS &&
        !bind.isOutgoingOnly() &&
        stateGlobal.svcStatus.value == SvcStatus.notReady &&
        !bind.isDisableSettings()) {
      return buildInstallCard(
        'Server unreachable',
        'Check your relay server address or network connection.',
        'Open server settings',
        () {
          DesktopSettingPage.switch2page(SettingsTabKey.network);
        },
        tone: 'danger',
      );
    }
    if (bind.isIncomingOnly()) {""",
        "Add cross-platform server unreachable recovery banner",
    )

    # Replace rustdesk.com Linux doc links with RRRemote repo URL
    repo_url = f"https://github.com/{update_repo}"
    txt = (
        txt.replace(
            "https://rustdesk.com/docs/en/client/linux/#permissions-issue",
            repo_url,
        )
        .replace(
            "https://rustdesk.com/docs/en/client/linux/#x11-required", repo_url
        )
        .replace(
            "https://rustdesk.com/docs/en/client/linux/#login-screen", repo_url
        )
    )

    # 7. Refactor buildInstallCard into semantic banner (amber warning / red danger / blue info)
    #    plus _buildMacTccChecklistCard helper
    txt = replace_exact(
        txt,
        """  Widget buildInstallCard(String title, String content, String btnText,
      GestureTapCallback onPressed,
      {double marginTop = 20.0,
      String? help,
      String? link,
      bool? closeButton,
      String? closeOption}) {
    if (bind.mainGetBuildinOption(key: kOptionHideHelpCards) == 'Y' &&
        content != 'install_daemon_tip') {
      return const SizedBox();
    }
    void closeCard() async {
      if (closeOption != null) {
        await bind.mainSetLocalOption(key: closeOption, value: 'N');
        if (bind.mainGetLocalOption(key: closeOption) == 'N') {
          setState(() {
            isCardClosed = true;
          });
        }
      } else {
        setState(() {
          isCardClosed = true;
        });
      }
    }

    return Stack(
      children: [
        Container(
          margin: EdgeInsets.fromLTRB(
              0, marginTop, 0, bind.isIncomingOnly() ? marginTop : 0),
          child: Container(
              decoration: BoxDecoration(
                  gradient: LinearGradient(
                begin: Alignment.centerLeft,
                end: Alignment.centerRight,
                colors: [
                  Color.fromARGB(255, 226, 66, 188),
                  Color.fromARGB(255, 244, 114, 124),
                ],
              )),
              padding: EdgeInsets.all(20),
              child: Column(
                  mainAxisAlignment: MainAxisAlignment.start,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: (title.isNotEmpty
                          ? <Widget>[
                              Center(
                                  child: Text(
                                translate(title),
                                style: TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 15),
                              ).marginOnly(bottom: 6)),
                            ]
                          : <Widget>[]) +
                      <Widget>[
                        if (content.isNotEmpty)
                          Text(
                            translate(content),
                            style: TextStyle(
                                height: 1.5,
                                color: Colors.white,
                                fontWeight: FontWeight.normal,
                                fontSize: 13),
                          ).marginOnly(bottom: 20)
                      ] +
                      (btnText.isNotEmpty
                          ? <Widget>[
                              Row(
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    FixedWidthButton(
                                      width: 150,
                                      padding: 8,
                                      isOutline: true,
                                      text: translate(btnText),
                                      textColor: Colors.white,
                                      borderColor: Colors.white,
                                      textSize: 20,
                                      radius: 10,
                                      onTap: onPressed,
                                    )
                                  ])
                            ]
                          : <Widget>[]) +
                      (help != null
                          ? <Widget>[
                              Center(
                                  child: InkWell(
                                      onTap: () async =>
                                          await launchUrl(Uri.parse(link!)),
                                      child: Text(
                                        translate(help),
                                        style: TextStyle(
                                            decoration:
                                                TextDecoration.underline,
                                            color: Colors.white,
                                            fontSize: 12),
                                      )).marginOnly(top: 6)),
                            ]
                          : <Widget>[]))),
        ),
        if (closeButton != null && closeButton == true)
          Positioned(
            top: 18,
            right: 0,
            child: IconButton(
              icon: Icon(
                Icons.close,
                color: Colors.white,
                size: 20,
              ),
              onPressed: closeCard,
            ),
          ),
      ],
    );
  }""",
        """  Widget _buildMacTccChecklistCard(
    BuildContext context, {
    required bool missingScreen,
    required bool missingAcc,
    required bool missingInput,
  }) {
    final c = RrColors.of(context);
    void openScreen() {
      bind.mainIsCanScreenRecording(prompt: true);
      launchUrl(Uri.parse(
          'x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'));
      watchIsCanScreenRecording = true;
    }

    void openAcc() {
      bind.mainIsProcessTrusted(prompt: true);
      launchUrl(Uri.parse(
          'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'));
      watchIsProcessTrust = true;
    }

    void openInput() {
      bind.mainIsCanInputMonitoring(prompt: true);
      launchUrl(Uri.parse(
          'x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent'));
      watchIsInputMonitoring = true;
    }

    Widget permRow(
      String title,
      String role,
      bool missing,
      VoidCallback onOpen,
    ) {
      final rowContent = ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 32),
        child: Padding(
          padding: const EdgeInsetsDirectional.fromSTEB(6, 4, 6, 4),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Icon(
                missing
                    ? Icons.radio_button_unchecked_rounded
                    : Icons.check_circle_rounded,
                size: 15,
                color: missing ? c.warningText : c.successText,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      title,
                      style: RrText.caption(
                        missing ? c.warningText : c.textSecondary,
                        weight: missing ? FontWeight.w600 : FontWeight.w500,
                      ),
                    ),
                    Text(
                      role,
                      style: TextStyle(
                        fontSize: 12,
                        height: 1.3,
                        color: missing ? c.warningText : c.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
              if (missing)
                Icon(
                  Icons.open_in_new_rounded,
                  size: 14,
                  color: c.warningText,
                ),
            ],
          ),
        ),
      );
      if (!missing) {
        return Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: rowContent,
        );
      }
      return Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: Semantics(
          button: true,
          label: 'Open System Settings for $title ($role)',
          child: Tooltip(
            message: 'Open $title in System Settings',
            child: Material(
              color: c.bgSurface,
              borderRadius: BorderRadius.circular(8),
              child: InkWell(
                borderRadius: BorderRadius.circular(8),
                onTap: onOpen,
                child: rowContent,
              ),
            ),
          ),
        ),
      );
    }

    void openNextSettings() {
      if (missingScreen) {
        openScreen();
      } else if (missingAcc) {
        openAcc();
      } else if (missingInput) {
        openInput();
      }
    }

    return Container(
      margin: const EdgeInsetsDirectional.fromSTEB(16, 8, 16, 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: c.warningSoft,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: c.warningSolid, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber_rounded,
                  size: 16, color: c.warningText),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  'macOS permissions required',
                  style: RrText.label(c.warningText, weight: FontWeight.w600),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          permRow(
            'Screen Recording',
            'View screen',
            missingScreen,
            openScreen,
          ),
          permRow(
            'Accessibility',
            'Mouse & keyboard control',
            missingAcc,
            openAcc,
          ),
          permRow(
            'Input Monitoring',
            'Keyboard shortcuts',
            missingInput,
            openInput,
          ),
          const SizedBox(height: 4),
          Text(
            'Quit and reopen RRRemote after granting permissions.',
            style: RrText.caption(c.warningText, weight: FontWeight.w400),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            height: 34,
            child: OutlinedButton(
              onPressed: openNextSettings,
              style: OutlinedButton.styleFrom(
                backgroundColor: c.bgSurface,
                foregroundColor: c.warningText,
                side: BorderSide(color: c.warningSolid, width: 1),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: Text(
                'Open System Settings',
                style: RrText.caption(c.warningText, weight: FontWeight.w600),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget buildInstallCard(String title, String content, String btnText,
      GestureTapCallback onPressed,
      {double marginTop = 8.0,
      String? help,
      String? link,
      bool? closeButton,
      String? closeOption,
      String tone = 'warning'}) {
    if (bind.mainGetBuildinOption(key: kOptionHideHelpCards) == 'Y' &&
        content != 'install_daemon_tip') {
      return const SizedBox();
    }
    void closeCard() async {
      if (closeOption != null) {
        await bind.mainSetLocalOption(key: closeOption, value: 'N');
        if (bind.mainGetLocalOption(key: closeOption) == 'N') {
          setState(() {
            isCardClosed = true;
          });
        }
      } else {
        setState(() {
          isCardClosed = true;
        });
      }
    }

    final c = RrColors.of(context);
    final bool isDanger = tone == 'danger';
    final bool isInfo = tone == 'info';
    final Color bg = isDanger
        ? c.dangerSoft
        : isInfo
            ? c.accentSoft
            : c.warningSoft;
    final Color border = isDanger
        ? c.dangerSolid
        : isInfo
            ? c.accentSolid
            : c.warningSolid;
    final Color fg = isDanger
        ? c.dangerText
        : isInfo
            ? c.accentText
            : c.warningText;
    final IconData leadingIcon = isDanger
        ? Icons.error_outline_rounded
        : isInfo
            ? Icons.system_update_alt_rounded
            : Icons.warning_amber_rounded;

    return Container(
      margin: EdgeInsetsDirectional.fromSTEB(
          16, marginTop, 16, bind.isIncomingOnly() ? marginTop : 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: border, width: 1),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Icon(leadingIcon, size: 16, color: fg),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  title.isNotEmpty ? translate(title) : translate('Status'),
                  style: RrText.label(fg, weight: FontWeight.w600),
                ),
              ),
              if (closeButton == true)
                Semantics(
                  button: true,
                  label: translate('Close'),
                  child: Tooltip(
                    message: translate('Close'),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(6),
                      onTap: closeCard,
                      child: SizedBox(
                        width: 28,
                        height: 28,
                        child: Icon(Icons.close_rounded, size: 16, color: fg),
                      ),
                    ),
                  ),
                ),
            ],
          ),
          if (content.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              translate(content),
              style: RrText.caption(fg, weight: FontWeight.w400),
            ),
          ],
          if (btnText.isNotEmpty) ...[
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              height: 34,
              child: isInfo
                  ? ElevatedButton(
                      onPressed: onPressed,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: c.accentSolid,
                        foregroundColor: Colors.white,
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      child: Text(
                        translate(btnText),
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    )
                  : OutlinedButton(
                      onPressed: onPressed,
                      style: OutlinedButton.styleFrom(
                        backgroundColor: c.bgSurface,
                        foregroundColor: fg,
                        side: BorderSide(color: border, width: 1),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      child: Text(
                        translate(btnText),
                        style: RrText.caption(fg, weight: FontWeight.w600),
                      ),
                    ),
            ),
          ],
          if (help != null && link != null) ...[
            const SizedBox(height: 8),
            InkWell(
              onTap: () async => await launchUrl(Uri.parse(link)),
              child: Text(
                translate(help),
                style: TextStyle(
                  decoration: TextDecoration.underline,
                  color: fg,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }""",
        "Semantic action banners (amber warning / red danger / accent info) + macOS TCC checklist",
    )

    write_text(p, txt)
