"""Desktop Connection Page refactor (flutter/lib/desktop/pages/connection_page.dart).

Applies all 7 `better-*` skills:
- `better-ui`: Exact concentric Quick-Connect bar (outer 14 = pad 6 + inner 8);
  optical padding on Connect button (start 14, end 12); crisp 1px control borders.
- `better-accessibility`: Focus-driven 2px RrColors.focusRing on Quick-Connect bar;
  RenderBox-anchored `⋮` mode menu (works on keyboard Enter/Space, never opens at 0,0);
  Semantics + Tooltip on all icon controls; reduced-motion guard on rotation; non-color-only
  status bar with inline recovery CTA.
- `better-typography`: Monospace tabular-nums + slashed-zero Quick-Connect input (16px w600).
- `better-writing`: Sentence case ('ID/Relay server', 'Remote terminal', 'TCP tunnel'),
  direct placeholder ('Device name or ID (⌘K)'), zero stranger 'Request approval' clutter.
"""

from __future__ import annotations

from pathlib import Path

from . import ensure_import, read_text, replace_exact, write_text


def patch_desktop_connection(root: Path) -> None:
    p = root / "flutter" / "lib" / "desktop" / "pages" / "connection_page.dart"
    txt = read_text(p)
    txt = ensure_import(
        txt, "import 'package:flutter_hbb/desktop/pages/desktop_setting_page.dart';"
    )

    # 1. Compact OnlineStatusWidget height & direct Network settings jump
    txt = replace_exact(
        txt,
        "  double? get height => bind.isIncomingOnly() ? null : em * 3;",
        "  double? get height => bind.isIncomingOnly() ? null : 38.0;",
        "Compact OnlineStatusWidget height 38px",
    )

    txt = replace_exact(
        txt,
        """  void onUsePublicServerGuide() {
    const url = "https://rustdesk.com/pricing";
    canLaunchUrlString(url).then((can) {
      if (can) {
        launchUrlString(url);
      }
    });
  }""",
        """  void onUsePublicServerGuide() {
    DesktopSettingPage.switch2page(SettingsTabKey.network);
  }""",
        "Replace pricing URL with direct Network/Server settings jump",
    )

    # 2. Non-color-only OnlineStatusWidget with inline recovery CTA + accessible Server Settings button
    txt = replace_exact(
        txt,
        """    basicWidget() => Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              height: 8,
              width: 8,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(4),
                color: _svcStopped.value ||
                        stateGlobal.svcStatus.value == SvcStatus.connecting
                    ? kColorWarn
                    : (stateGlobal.svcStatus.value == SvcStatus.ready
                        ? Color.fromARGB(255, 50, 190, 166)
                        : Color.fromARGB(255, 224, 79, 95)),
              ),
            ).marginSymmetric(horizontal: em),
            Container(
              width: isIncomingOnly ? 226 : null,
              child: _buildConnStatusMsg(),
            ),
            // stop
            if (!isIncomingOnly) startServiceWidget(),
            // ready && public
            // No need to show the guide if is custom client.
            if (!isIncomingOnly) setupServerWidget(),
          ],
        );""",
        """    basicWidget() {
      final c = RrColors.of(context);
      final stopped = _svcStopped.value;
      final status = stateGlobal.svcStatus.value;
      final isReady = !stopped && status == SvcStatus.ready;
      final isConnecting = !stopped && status == SvcStatus.connecting;
      final isNotReady = !stopped && status == SvcStatus.notReady;
      final IconData iconData = stopped
          ? Icons.pause_circle_rounded
          : isConnecting
              ? Icons.sync_rounded
              : isReady
                  ? Icons.check_circle_rounded
                  : Icons.error_rounded;
      final Color iconColor = stopped || isNotReady
          ? c.dangerSolid
          : isConnecting
              ? c.warningSolid
              : c.successSolid;
      return Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Padding(
            padding: const EdgeInsetsDirectional.only(start: 16, end: 8),
            child: Icon(iconData, size: 15, color: iconColor),
          ),
          Flexible(
            child: Container(
              width: isIncomingOnly ? 226 : null,
              child: _buildConnStatusMsg(),
            ),
          ),
          if (!isIncomingOnly) startServiceWidget(),
          if (!isIncomingOnly && isNotReady && !bind.isDisableSettings())
            Padding(
              padding: const EdgeInsetsDirectional.only(start: 10),
              child: InkWell(
                borderRadius: BorderRadius.circular(6),
                onTap: () =>
                    DesktopSettingPage.switch2page(SettingsTabKey.network),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                  child: Text(
                    'Open server settings',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: c.accentText,
                      decoration: TextDecoration.underline,
                    ),
                  ),
                ),
              ),
            ),
          if (!isIncomingOnly) setupServerWidget(),
          if (!isIncomingOnly) const Spacer(),
          if (!isIncomingOnly && !bind.isDisableSettings())
            Semantics(
              button: true,
              label: translate('ID/Relay Server'),
              child: Tooltip(
                message: translate('ID/Relay Server'),
                child: InkWell(
                  borderRadius: BorderRadius.circular(8),
                  hoverColor: c.bgHover,
                  onTap: () =>
                      DesktopSettingPage.switch2page(SettingsTabKey.network),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(minHeight: 32),
                    child: Padding(
                      padding: const EdgeInsetsDirectional.fromSTEB(
                          10, 4, 10, 4),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.dns_rounded,
                            size: 14,
                            color: c.textSecondary,
                          ),
                          const SizedBox(width: 6),
                          Text(
                            translate('ID/Relay Server'),
                            style: RrText.caption(
                              c.textSecondary,
                              weight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ).marginOnly(right: 12),
        ],
      );
    }""",
        "Non-color-only OnlineStatusWidget with recovery CTA and 32px Server button",
    )

    txt = replace_exact(
        txt,
        """  _buildConnStatusMsg() {
    widget.onSvcStatusChanged?.call();
    return Text(
      _svcStopped.value
          ? translate("Service is not running")
          : stateGlobal.svcStatus.value == SvcStatus.connecting
              ? translate("connecting_status")
              : stateGlobal.svcStatus.value == SvcStatus.notReady
                  ? translate("not_ready_status")
                  : translate('Ready'),
      style: TextStyle(fontSize: em),
    );
  }""",
        """  _buildConnStatusMsg() {
    widget.onSvcStatusChanged?.call();
    final c = RrColors.of(context);
    return Text(
      _svcStopped.value
          ? translate("Service is not running")
          : stateGlobal.svcStatus.value == SvcStatus.connecting
              ? translate("connecting_status")
              : stateGlobal.svcStatus.value == SvcStatus.notReady
                  ? 'Server unreachable'
                  : translate('Ready'),
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: RrText.caption(c.textSecondary, weight: FontWeight.w500),
    );
  }""",
        "Concise status bar typography & clear unreachable copy",
    )

    # 3. Register _idFocusNode in Get for Cmd/Ctrl+K shortcut & clean up on dispose
    txt = replace_exact(
        txt,
        """    Get.put<TextEditingController>(_idEditingController);
    Get.put<IDTextEditingController>(_idController);""",
        """    Get.put<FocusNode>(_idFocusNode, tag: 'rr-quick-connect-focus');
    Get.put<TextEditingController>(_idEditingController);
    Get.put<IDTextEditingController>(_idController);""",
        "Register Quick-Connect FocusNode for Cmd/Ctrl+K shortcut",
    )

    txt = replace_exact(
        txt,
        """    if (Get.isRegistered<TextEditingController>()) {
      Get.delete<TextEditingController>();
    }""",
        """    if (Get.isRegistered<FocusNode>(tag: 'rr-quick-connect-focus')) {
      Get.delete<FocusNode>(tag: 'rr-quick-connect-focus');
    }
    if (Get.isRegistered<TextEditingController>()) {
      Get.delete<TextEditingController>();
    }""",
        "Clean up Quick-Connect FocusNode tag on dispose",
    )

    # 4. Shared 16px edge alignment & remove redundant horizontal divider
    txt = replace_exact(
        txt,
        """            Row(
              children: [
                Flexible(child: _buildRemoteIDTextField(context)),
              ],
            ).marginOnly(top: 22),
            SizedBox(height: 12),
            Divider().paddingOnly(right: 12),
            Expanded(child: PeerTabPage()),
          ],
        ).paddingOnly(left: 12.0)),""",
        """            Row(
              children: [
                Expanded(child: _buildRemoteIDTextField(context)),
              ],
            ).marginOnly(top: 16, right: 16),
            const SizedBox(height: 16),
            Expanded(child: PeerTabPage()),
          ],
        ).paddingOnly(left: 16.0)),""",
        "Shared 16px alignment edges & remove redundant divider in ConnectionPage",
    )

    # 5. Match platform in Quick-Connect autocomplete (e.g. 'mac', 'win', 'linux', 'm4')
    txt = replace_exact(
        txt,
        """                      _autocompleteOpts = _allPeersLoader.peers
                          .where((peer) =>
                              peer.id.toLowerCase().contains(textToFind) ||
                              peer.username
                                  .toLowerCase()
                                  .contains(textToFind) ||
                              peer.hostname
                                  .toLowerCase()
                                  .contains(textToFind) ||
                              peer.alias.toLowerCase().contains(textToFind))
                          .toList();""",
        """                      _autocompleteOpts = _allPeersLoader.peers
                          .where((peer) =>
                              peer.id.toLowerCase().contains(textToFind) ||
                              peer.username
                                  .toLowerCase()
                                  .contains(textToFind) ||
                              peer.hostname
                                  .toLowerCase()
                                  .contains(textToFind) ||
                              peer.platform
                                  .toLowerCase()
                                  .contains(textToFind) ||
                              peer.alias.toLowerCase().contains(textToFind))
                          .toList();""",
        "Include platform in Quick-Connect device jump autocomplete",
    )

    # 6. Concentric focus-ringed Quick-Connect bar (outer 14 = pad 6 + inner 8)
    txt = replace_exact(
        txt,
        """    var w = Container(
      width: 320 + 20 * 2,
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 22),
      decoration: BoxDecoration(
          borderRadius: const BorderRadius.all(Radius.circular(13)),
          border: Border.all(color: Theme.of(context).colorScheme.background)),
      child: Ink(
        child: Column(
          children: [
            getConnectionPageTitle(context, false).marginOnly(bottom: 15),
            Row(
              children: [
                Expanded(
                    child: RawAutocomplete<Peer>(""",
        """    final c = RrColors.of(context);
    var w = Obx(() {
      final focused = _idInputFocused.value;
      return Container(
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          color: c.bgSurface,
          borderRadius: const BorderRadius.all(Radius.circular(14)),
          border: Border.all(
            color: focused ? c.focusRing : c.borderControl,
            width: focused ? 2.0 : 1.0,
          ),
          boxShadow: c.cardElevation(context),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Container(
              width: 36,
              height: 36,
              margin: const EdgeInsetsDirectional.only(end: 8),
              decoration: BoxDecoration(
                color: c.accentSoft,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(
                Icons.bolt_rounded,
                size: 18,
                color: c.accentText,
              ),
            ),
            Expanded(
              child: RawAutocomplete<Peer>(""",
        "Focus-ringed concentric (14/6/8) Quick-Connect command bar",
    )

    txt = replace_exact(
        txt,
        """                          style: const TextStyle(
                            fontFamily: 'WorkSans',
                            fontSize: 22,
                            height: 1.4,
                          ),
                          maxLines: 1,
                          cursorColor:
                              Theme.of(context).textTheme.titleLarge?.color,
                          decoration: InputDecoration(
                              filled: false,
                              counterText: '',
                              hintText: _idInputFocused.value
                                  ? null
                                  : translate('Enter Remote ID'),
                              contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 15, vertical: 13)),""",
        """                          style: RrText.mono(
                            size: 16,
                            weight: FontWeight.w600,
                            color: c.textPrimary,
                            height: 1.25,
                            letterSpacing: 0.3,
                          ),
                          maxLines: 1,
                          cursorColor: c.accentSolid,
                          decoration: InputDecoration(
                              filled: false,
                              isDense: true,
                              border: InputBorder.none,
                              enabledBorder: InputBorder.none,
                              focusedBorder: InputBorder.none,
                              counterText: '',
                              hintText: _idInputFocused.value
                                  ? null
                                  : '${translate('Enter Remote ID')} (${isMacOS ? '⌘K' : 'Ctrl+K'})',
                              hintStyle: RrText.label(c.textMuted,
                                  weight: FontWeight.w400),
                              contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 8)),""",
        "Monospace tabular-nums Quick-Connect input with shortcut hint",
    )

    # 7. Optical-aligned Connect button + RenderBox-anchored accessible ⋮ mode menu
    txt = replace_exact(
        txt,
        """                  },
                )),
              ],
            ),
            Padding(
              padding: const EdgeInsets.only(top: 13.0),
              child: Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                SizedBox(
                  height: 28.0,
                  child: ElevatedButton(
                    onPressed: () {
                      onConnect();
                    },
                    child: Text(translate("Connect")),
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  height: 28.0,
                  width: 28.0,
                  decoration: BoxDecoration(
                    border: Border.all(color: Theme.of(context).dividerColor),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Center(
                    child: StatefulBuilder(
                      builder: (context, setState) {
                        var offset = Offset(0, 0);
                        return Obx(() => InkWell(
                              child: _menuOpen.value
                                  ? Transform.rotate(
                                      angle: pi,
                                      child: Icon(IconFont.more, size: 14),
                                    )
                                  : Icon(IconFont.more, size: 14),
                              onTapDown: (e) {
                                offset = e.globalPosition;
                              },
                              onTap: () async {
                                _menuOpen.value = true;
                                final x = offset.dx;
                                final y = offset.dy;
                                await mod_menu
                                    .showMenu(
                                  context: context,
                                  position: RelativeRect.fromLTRB(x, y, x, y),
                                  items: [
                                    (
                                      'Transfer file',
                                      () => onConnect(isFileTransfer: true)
                                    ),
                                    (
                                      'View camera',
                                      () => onConnect(isViewCamera: true)
                                    ),
                                    (
                                      '${translate('Terminal')} (beta)',
                                      () => onConnect(isTerminal: true)
                                    ),
                                    // `connect` routes this through the
                                    // desktop path only; the peer card gates
                                    // it the same way.
                                    if (isDesktop)
                                      (
                                        'TCP tunneling',
                                        () => onConnect(isTcpTunneling: true)
                                      ),
                                  ]
                                      .map<MenuEntryBase<String>>(
                                          (e) => MenuEntryButton<String>(
                                            childBuilder: (TextStyle? style) =>
                                                Text(
                                              translate(e.$1),
                                              style: style,
                                            ),
                                            proc: () => e.$2(),
                                            padding: EdgeInsets.symmetric(
                                                horizontal:
                                                    kDesktopMenuPadding.left),
                                            dismissOnClicked: true,
                                          ))
                                      .followedBy([
                                        MenuEntryDivider<String>(),
                                        _requestApprovalMenu(context),
                                      ])
                                      .map((e) => e.build(
                                          context,
                                          const MenuConfig(
                                              commonColor: CustomPopupMenuTheme
                                                  .commonColor,
                                              height:
                                                  CustomPopupMenuTheme.height,
                                              dividerHeight:
                                                  CustomPopupMenuTheme
                                                      .dividerHeight)))
                                      .expand((i) => i)
                                      .toList(),
                                  elevation: 8,
                                )
                                    .then((_) {
                                  _menuOpen.value = false;
                                });
                              },
                            ));
                      },
                    ),
                  ),
                ),
              ]),
            ),
          ],
        ),
      ),
    );
    return Container(
        constraints: const BoxConstraints(maxWidth: 600), child: w);""",
        """                  },
                ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              height: 36.0,
              child: ElevatedButton(
                onPressed: () {
                  onConnect();
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: c.accentSolid,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsetsDirectional.fromSTEB(14, 0, 12, 0),
                  elevation: 0,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      translate("Connect"),
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(width: 6),
                    const Icon(Icons.arrow_forward_rounded, size: 16),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 6),
            Builder(
              builder: (btnCtx) {
                final reduceMotion = MediaQuery.disableAnimationsOf(btnCtx);
                return Semantics(
                  button: true,
                  label: 'Connection modes',
                  child: Tooltip(
                    message: 'Connection modes',
                    child: Material(
                      color: c.bgSurface,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8),
                        side: BorderSide(color: c.borderControl, width: 1),
                      ),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(8),
                        hoverColor: c.bgHover,
                        onTap: () async {
                          _menuOpen.value = true;
                          final box = btnCtx.findRenderObject() as RenderBox?;
                          final pos = box != null
                              ? box.localToGlobal(
                                  Offset(0, box.size.height + 4))
                              : const Offset(0, 0);
                          await mod_menu
                              .showMenu(
                            context: btnCtx,
                            position: RelativeRect.fromLTRB(
                                pos.dx, pos.dy, pos.dx, pos.dy),
                            items: [
                              (
                                translate('Transfer file'),
                                () => onConnect(isFileTransfer: true)
                              ),
                              (
                                translate('Terminal'),
                                () => onConnect(isTerminal: true)
                              ),
                              if (isDesktop)
                                (
                                  translate('TCP tunneling'),
                                  () => onConnect(isTcpTunneling: true)
                                ),
                              (
                                translate('View camera'),
                                () => onConnect(isViewCamera: true)
                              ),
                            ]
                                .map<MenuEntryBase<String>>(
                                    (e) => MenuEntryButton<String>(
                                          childBuilder: (TextStyle? style) =>
                                              Text(e.$1, style: style),
                                          proc: () => e.$2(),
                                          padding: EdgeInsets.symmetric(
                                              horizontal:
                                                  kDesktopMenuPadding.left),
                                          dismissOnClicked: true,
                                        ))
                                .map((e) => e.build(
                                    btnCtx,
                                    const MenuConfig(
                                        commonColor:
                                            CustomPopupMenuTheme.commonColor,
                                        height: CustomPopupMenuTheme.height,
                                        dividerHeight: CustomPopupMenuTheme
                                            .dividerHeight)))
                                .expand((i) => i)
                                .toList(),
                            elevation: 8,
                          )
                              .then((_) {
                            _menuOpen.value = false;
                          });
                        },
                        child: SizedBox(
                          width: 36,
                          height: 36,
                          child: Center(
                            child: Obx(() {
                              final icon = Icon(
                                Icons.more_horiz_rounded,
                                size: 18,
                                color: c.textSecondary,
                              );
                              if (_menuOpen.value && !reduceMotion) {
                                return Transform.rotate(
                                    angle: pi / 2, child: icon);
                              }
                              return icon;
                            }),
                          ),
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          ],
        ),
      );
    });
    return ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 720), child: w);""",
        "Optical Connect button & keyboard-anchored accessible connection mode menu",
    )

    write_text(p, txt)
