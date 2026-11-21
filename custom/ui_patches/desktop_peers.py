"""Personal-first peer tabs, search/filter, empty states, and 1-click accessible PeerCard.

Targets:
- flutter/lib/models/peer_tab_model.dart
- flutter/lib/common/widgets/peer_tab_page.dart
- flutter/lib/common/widgets/peers_view.dart
- flutter/lib/common/widgets/peer_card.dart
"""

from __future__ import annotations

from pathlib import Path

from . import read_text, replace_exact, write_text


def patch_desktop_peers(root: Path) -> None:
    # ------------------------------------------------------------------
    # 1. peer_tab_model.dart: Favorites -> Recent -> LAN, outline/filled state icons
    # ------------------------------------------------------------------
    model_p = root / "flutter" / "lib" / "models" / "peer_tab_model.dart"
    mtxt = read_text(model_p)
    mtxt = replace_exact(
        mtxt,
        """  final List<int> orders =
      List.generate(maxTabCount, (index) => index, growable: false);""",
        """  final List<int> orders = [1, 0, 2, 3, 4];""",
        "Order peer tabs as Favorites, Recent, LAN by default",
    )
    mtxt = replace_exact(
        mtxt,
        """    // init currentTab
    _currentTab =
        int.tryParse(bind.getLocalFlutterOption(k: kOptionPeerTabIndex)) ?? 0;""",
        """    // init currentTab (default to Favorites for personal fleet UX)
    _currentTab =
        int.tryParse(bind.getLocalFlutterOption(k: kOptionPeerTabIndex)) ??
            PeerTabIndex.fav.index;""",
        "Default active peer tab to Favorites",
    )
    mtxt = replace_exact(
        mtxt,
        """  IconData tabIcon(int index) {
    if (index >= 0 && index < icons.length) {
      return icons[index];
    }
    return Icons.help;
  }""",
        """  IconData tabIcon(int index, {bool selected = true}) {
    switch (index) {
      case 0:
        return selected ? Icons.history_rounded : Icons.schedule_rounded;
      case 1:
        return selected ? Icons.star_rounded : Icons.star_outline_rounded;
      case 2:
        return selected ? Icons.lan_rounded : Icons.lan_outlined;
      case 3:
        return IconFont.addressBook;
      case 4:
        return selected
            ? IconFont.deviceGroupFill
            : IconFont.deviceGroupOutline;
      default:
        return Icons.devices_other_rounded;
    }
  }""",
        "Outline inactive / filled active Material Rounded icons in PeerTabModel",
    )
    write_text(model_p, mtxt)

    # ------------------------------------------------------------------
    # 2. peer_tab_page.dart: AA-verified pill tabs, Online-only toggle, accessible search & dropdowns
    # ------------------------------------------------------------------
    tab_p = root / "flutter" / "lib" / "common" / "widgets" / "peer_tab_page.dart"
    ttxt = read_text(tab_p)
    ttxt = replace_exact(
        ttxt,
        """        Obx(() => SizedBox(
              height: 32,
              child: Container(
                padding: stateGlobal.isPortrait.isTrue
                    ? EdgeInsets.symmetric(horizontal: 2)
                    : null,
                child: selectionWrap(Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                        child: visibleContextMenuListener(
                            _createSwitchBar(context))),
                    if (stateGlobal.isPortrait.isTrue)
                      ..._portraitRightActions(context)
                    else
                      ..._landscapeRightActions(context)
                  ],
                )),
              ),
            ).paddingOnly(right: stateGlobal.isPortrait.isTrue ? 0 : 12)),""",
        """        Obx(() => SizedBox(
              height: 38,
              child: Container(
                padding: stateGlobal.isPortrait.isTrue
                    ? const EdgeInsets.symmetric(horizontal: 2)
                    : null,
                child: selectionWrap(Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                        child: visibleContextMenuListener(
                            _createSwitchBar(context))),
                    if (stateGlobal.isPortrait.isTrue)
                      ..._portraitRightActions(context)
                    else
                      ..._landscapeRightActions(context)
                  ],
                )),
              ),
            ).paddingOnly(right: stateGlobal.isPortrait.isTrue ? 0 : 16)),""",
        "PeerTabPage switch bar height 38px & 16px trailing edge",
    )

    ttxt = replace_exact(
        ttxt,
        """          final selected = model.currentTab == t;
          final color = selected
              ? MyTheme.tabbar(context).selectedTextColor
              : MyTheme.tabbar(context).unSelectedTextColor
            ?..withOpacity(0.5);
          final hover = false.obs;
          final deco = BoxDecoration(
              color: Theme.of(context).colorScheme.background,
              borderRadius: BorderRadius.circular(6));
          final decoBorder = BoxDecoration(
              border: Border(
            bottom: BorderSide(width: 2, color: color!),
          ));
          counter += 1;
          return ReorderableDragStartListener(
              key: ValueKey(t),
              index: counter,
              child: Obx(() => Tooltip(
                    preferBelow: false,
                    message: model.tabTooltip(t),
                    onTriggered: isMobile ? mobileShowTabVisibilityMenu : null,
                    child: InkWell(
                      child: Container(
                        decoration: (hover.value
                            ? (selected ? decoBorder : deco)
                            : (selected ? decoBorder : null)),
                        child: Icon(model.tabIcon(t), color: color)
                            .paddingSymmetric(horizontal: 4),
                      ).paddingSymmetric(horizontal: 4),
                      onTap: isOptionFixed(kOptionPeerTabIndex)
                          ? null
                          : () async {
                              await handleTabSelection(t);
                              await bind.setLocalFlutterOption(
                                  k: kOptionPeerTabIndex, v: t.toString());
                            },
                      onHover: (value) => hover.value = value,
                    ),
                  )));""",
        """          final c = RrColors.of(context);
          final selected = model.currentTab == t;
          final isPortrait = stateGlobal.isPortrait.isTrue;
          final fgColor = selected ? c.accentText : c.textSecondary;
          final hover = false.obs;
          final focused = false.obs;
          counter += 1;
          return ReorderableDragStartListener(
              key: ValueKey(t),
              index: counter,
              child: Obx(() => Semantics(
                    button: true,
                    selected: selected,
                    label: model.tabTooltip(t),
                    child: Tooltip(
                      preferBelow: false,
                      message: model.tabTooltip(t),
                      onTriggered: isMobile ? mobileShowTabVisibilityMenu : null,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(8),
                        onFocusChange: (f) => focused.value = f,
                        child: Container(
                          margin: const EdgeInsetsDirectional.only(end: 6),
                          padding: EdgeInsetsDirectional.fromSTEB(
                              isPortrait ? 10 : 10, 6, isPortrait ? 10 : 12, 6),
                          decoration: BoxDecoration(
                            color: selected
                                ? c.accentSoft
                                : (hover.value ? c.bgHover : Colors.transparent),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: focused.value
                                  ? c.focusRing
                                  : Colors.transparent,
                              width: focused.value ? 2 : 1,
                            ),
                          ),
                          child: isPortrait
                              ? Icon(model.tabIcon(t, selected: selected),
                                  size: 18, color: fgColor)
                              : Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(model.tabIcon(t, selected: selected),
                                        size: 16, color: fgColor),
                                    const SizedBox(width: 6),
                                    Text(
                                      model.tabTooltip(t),
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: selected
                                            ? FontWeight.w600
                                            : FontWeight.w500,
                                        color: fgColor,
                                      ),
                                    ),
                                  ],
                                ),
                        ),
                        onTap: isOptionFixed(kOptionPeerTabIndex)
                            ? null
                            : () async {
                                await handleTabSelection(t);
                                await bind.setLocalFlutterOption(
                                    k: kOptionPeerTabIndex, v: t.toString());
                              },
                        onHover: (value) => hover.value = value,
                      ),
                    ),
                  )));""",
        "AA-verified labeled pill tabs with outline/filled icons & focus rings",
    )

    # Add Online-only filter chip into _landscapeRightActions
    ttxt = replace_exact(
        ttxt,
        """  List<Widget> _landscapeRightActions(BuildContext context) {
    final model = Provider.of<PeerTabModel>(context);
    return [
      const PeerSearchBar().marginOnly(right: 13),""",
        """  Widget _createOnlineOnlyChip(BuildContext context) {
    final c = RrColors.of(context);
    return Obx(() {
      final active = peerOnlineOnly.value == 'Y';
      return Semantics(
        button: true,
        toggled: active,
        label: 'Online devices only',
        child: Tooltip(
          message: 'Online devices only',
          child: Material(
            color: active ? c.successSoft : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            child: InkWell(
              borderRadius: BorderRadius.circular(8),
              hoverColor: active ? c.successSoft : c.bgHover,
              onTap: () {
                peerOnlineOnly.value = active ? '' : 'Y';
              },
              child: Container(
                height: 32,
                padding: const EdgeInsetsDirectional.fromSTEB(8, 0, 10, 0),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: active ? c.successSolid : c.borderSubtle,
                    width: 1,
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: active ? c.successSolid : Colors.transparent,
                        border: active
                            ? null
                            : Border.all(color: c.offlineSolid, width: 1.5),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      translate('Online'),
                      style: RrText.caption(
                        active ? c.successText : c.textSecondary,
                        weight: active ? FontWeight.w600 : FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    });
  }

  List<Widget> _landscapeRightActions(BuildContext context) {
    final model = Provider.of<PeerTabModel>(context);
    return [
      _createOnlineOnlyChip(context).marginOnly(right: 8),
      const PeerSearchBar().marginOnly(right: 8),""",
        "Add 1-click Online-only filter chip in PeerTabPage toolbar",
    )

    # Polish PeerSearchBar with focus ring, accessible labels, and >=32px clear button
    ttxt = replace_exact(
        ttxt,
        """    return Obx(() => Container(
          width: stateGlobal.isPortrait.isTrue ? 120 : 140,
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.background,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Row(
            children: [
              Expanded(
                child: Row(
                  children: [
                    Icon(
                      Icons.search_rounded,
                      color: Theme.of(context).hintColor,
                    ).marginSymmetric(horizontal: 4),
                    Expanded(
                      child: TextField(
                        autofocus: true,
                        controller: peerSearchTextController,
                        onChanged: (searchText) {
                          peerSearchText.value = searchText;
                        },
                        focusNode: focusNode,
                        textAlign: TextAlign.start,
                        maxLines: 1,
                        cursorColor: Theme.of(context)
                            .textTheme
                            .titleLarge
                            ?.color
                            ?.withOpacity(0.5),
                        cursorHeight: 18,
                        cursorWidth: 1,
                        style: const TextStyle(fontSize: 14),
                        decoration: InputDecoration(
                          contentPadding:
                              const EdgeInsets.symmetric(vertical: 6),
                          hintText:
                              focused.value ? null : translate("Search ID"),
                          hintStyle: TextStyle(
                              fontSize: 14, color: Theme.of(context).hintColor),
                          border: InputBorder.none,
                          isDense: true,
                        ),
                      ).workaroundFreezeLinuxMint(),
                    ),
                    // Icon(Icons.close),
                    IconButton(
                      alignment: Alignment.centerRight,
                      padding: const EdgeInsets.only(right: 2),
                      onPressed: () {
                        setState(() {
                          peerSearchTextController.clear();
                          peerSearchText.value = "";
                          drawer = false;
                        });
                      },
                      icon: Tooltip(
                          message: translate('Close'),
                          child: Icon(
                            Icons.close,
                            color: Theme.of(context).hintColor,
                          )),
                    ),
                  ],
                ),
              )
            ],
          ),
        ));""",
        """    final c = RrColors.of(context);
    return Obx(() => Container(
          width: stateGlobal.isPortrait.isTrue ? 136 : 176,
          height: 32,
          decoration: BoxDecoration(
            color: c.bgSurface,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: focused.value ? c.focusRing : c.borderControl,
              width: focused.value ? 2 : 1,
            ),
          ),
          child: Row(
            children: [
              Padding(
                padding: const EdgeInsetsDirectional.only(start: 8, end: 4),
                child: Icon(
                  Icons.search_rounded,
                  size: 16,
                  color: c.textMuted,
                ),
              ),
              Expanded(
                child: TextField(
                  autofocus: true,
                  controller: peerSearchTextController,
                  onChanged: (searchText) {
                    peerSearchText.value = searchText;
                  },
                  focusNode: focusNode,
                  textAlign: TextAlign.start,
                  maxLines: 1,
                  cursorColor: c.accentSolid,
                  style: TextStyle(
                    fontSize: stateGlobal.isPortrait.isTrue ? 16 : 13,
                    color: c.textPrimary,
                  ),
                  decoration: InputDecoration(
                    filled: false,
                    contentPadding: const EdgeInsets.symmetric(vertical: 6),
                    hintText: translate("Search ID"),
                    hintStyle: TextStyle(
                      fontSize: stateGlobal.isPortrait.isTrue ? 16 : 13,
                      color: c.textMuted,
                    ),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    isDense: true,
                  ),
                ).workaroundFreezeLinuxMint(),
              ),
              Semantics(
                button: true,
                label: 'Clear filter',
                child: Tooltip(
                  message: 'Clear filter',
                  child: InkWell(
                    borderRadius: BorderRadius.circular(6),
                    onTap: () {
                      setState(() {
                        peerSearchTextController.clear();
                        peerSearchText.value = "";
                        drawer = false;
                      });
                    },
                    child: SizedBox(
                      width: 28,
                      height: 28,
                      child: Icon(
                        Icons.close_rounded,
                        size: 16,
                        color: c.textSecondary,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ));""",
        "Focus-ringed PeerSearchBar with 16px mobile text & accessible Clear button",
    )

    # Upgrade _hoverAction to >=32x32px target with Semantics & RrColors
    ttxt = replace_exact(
        ttxt,
        """Widget _hoverAction(
    {required BuildContext context,
    required Widget child,
    required Function() onTap,
    required String toolTip,
    GestureTapDownCallback? onTapDown,
    RxBool? hoverableWhenfalse,
    EdgeInsetsGeometry padding = const EdgeInsets.all(4.0)}) {
  final hover = false.obs;
  final deco = BoxDecoration(
    color: Theme.of(context).colorScheme.background,
    borderRadius: BorderRadius.circular(6),
  );
  return Tooltip(
    message: toolTip,
    child: Obx(
      () => Container(
          margin: EdgeInsets.symmetric(horizontal: 1),
          decoration:
              (hover.value || hoverableWhenfalse?.value == false) ? deco : null,
          child: InkWell(
              onHover: (value) => hover.value = value,
              onTap: onTap,
              onTapDown: onTapDown,
              child: Container(padding: padding, child: child))),
    ),
  );
}""",
        """Widget _hoverAction(
    {required BuildContext context,
    required Widget child,
    required Function() onTap,
    required String toolTip,
    GestureTapDownCallback? onTapDown,
    RxBool? hoverableWhenfalse,
    EdgeInsetsGeometry padding = const EdgeInsets.all(6.0)}) {
  final c = RrColors.of(context);
  final hover = false.obs;
  final deco = BoxDecoration(
    color: c.bgHover,
    borderRadius: BorderRadius.circular(8),
  );
  return Semantics(
    button: true,
    label: toolTip,
    child: Tooltip(
      message: toolTip,
      child: Obx(
        () => Container(
            margin: const EdgeInsets.symmetric(horizontal: 2),
            decoration: (hover.value || hoverableWhenfalse?.value == false)
                ? deco
                : null,
            child: InkWell(
                borderRadius: BorderRadius.circular(8),
                onHover: (value) => hover.value = value,
                onTap: onTap,
                onTapDown: onTapDown,
                child: ConstrainedBox(
                    constraints:
                        const BoxConstraints(minWidth: 32, minHeight: 32),
                    child: Center(
                        child: Padding(padding: padding, child: child))))),
      ),
    ),
  );
}""",
        "Accessible >=32x32px _hoverAction toolbar buttons",
    )

    # RenderBox-anchor PeerViewDropdown & PeerSortDropdown so keyboard activation works
    ttxt = replace_exact(
        ttxt,
        """    var menuPos = RelativeRect.fromLTRB(0, 0, 0, 0);
    return _hoverAction(
        context: context,
        toolTip: translate('Change view'),
        child: Icon(
          peerCardUiType.value == PeerUiType.grid
              ? Icons.grid_view_rounded
              : peerCardUiType.value == PeerUiType.list
                  ? Icons.view_list_rounded
                  : Icons.view_agenda_rounded,
          size: 18,
        ),
        onTapDown: (details) {
          final x = details.globalPosition.dx;
          final y = details.globalPosition.dy;
          menuPos = RelativeRect.fromLTRB(x, y, x, y);
        },
        onTap: () => showMenu(
              context: context,
              position: menuPos,
              items: items,
              elevation: 8,
            ));""",
        """    return Builder(
      builder: (btnCtx) => _hoverAction(
          context: btnCtx,
          toolTip: translate('Change view'),
          child: Icon(
            peerCardUiType.value == PeerUiType.grid
                ? Icons.grid_view_rounded
                : peerCardUiType.value == PeerUiType.list
                    ? Icons.view_list_rounded
                    : Icons.view_agenda_rounded,
            size: 18,
          ),
          onTap: () {
            final box = btnCtx.findRenderObject() as RenderBox?;
            final pos = box != null
                ? box.localToGlobal(Offset(0, box.size.height + 4))
                : const Offset(0, 0);
            showMenu(
              context: btnCtx,
              position:
                  RelativeRect.fromLTRB(pos.dx, pos.dy, pos.dx, pos.dy),
              items: items,
              elevation: 8,
            );
          }),
    );""",
        "RenderBox-anchored PeerViewDropdown for keyboard & pointer",
    )

    ttxt = replace_exact(
        ttxt,
        """    var menuPos = RelativeRect.fromLTRB(0, 0, 0, 0);
    return _hoverAction(
      context: context,
      toolTip: translate('Sort by'),
      child: Icon(
        Icons.sort_rounded,
        size: 18,
      ),
      onTapDown: (details) {
        final x = details.globalPosition.dx;
        final y = details.globalPosition.dy;
        menuPos = RelativeRect.fromLTRB(x, y, x, y);
      },
      onTap: () => showMenu(
        context: context,
        position: menuPos,
        items: items,
        elevation: 8,
      ),
    );""",
        """    return Builder(
      builder: (btnCtx) => _hoverAction(
        context: btnCtx,
        toolTip: translate('Sort by'),
        child: const Icon(
          Icons.sort_rounded,
          size: 18,
        ),
        onTap: () {
          final box = btnCtx.findRenderObject() as RenderBox?;
          final pos = box != null
              ? box.localToGlobal(Offset(0, box.size.height + 4))
              : const Offset(0, 0);
          showMenu(
            context: btnCtx,
            position: RelativeRect.fromLTRB(pos.dx, pos.dy, pos.dx, pos.dy),
            items: items,
            elevation: 8,
          );
        },
      ),
    );""",
        "RenderBox-anchored PeerSortDropdown for keyboard & pointer",
    )
    write_text(tab_p, ttxt)

    # ------------------------------------------------------------------
    # 3. peers_view.dart: Online-only reactive filter + forward-pointing empty & no-match states
    # ------------------------------------------------------------------
    pv_p = root / "flutter" / "lib" / "common" / "widgets" / "peers_view.dart"
    pvtxt = read_text(pv_p)

    pvtxt = replace_exact(
        pvtxt,
        """/// for peer search text, global obs value
final peerSearchText = "".obs;

/// for peer sort, global obs value
RxString? _peerSort;
RxString get peerSort {
  _peerSort ??= bind.getLocalFlutterOption(k: kOptionPeerSorting).obs;
  return _peerSort!;
}

// list for listener
RxList<RxString> get obslist => [peerSearchText, peerSort].obs;""",
        """/// for peer search text, global obs value
final peerSearchText = "".obs;

/// for online-only personal fleet filter ('Y' or '')
final peerOnlineOnly = "".obs;

/// for peer sort, global obs value
RxString? _peerSort;
RxString get peerSort {
  _peerSort ??= bind.getLocalFlutterOption(k: kOptionPeerSorting).obs;
  return _peerSort!;
}

// list for listener
RxList<RxString> get obslist => [peerSearchText, peerSort, peerOnlineOnly].obs;""",
        "Add reactive peerOnlineOnly filter to peers_view.dart",
    )

    pvtxt = replace_exact(
        pvtxt,
        """          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.sentiment_very_dissatisfied_rounded,
                  color: Theme.of(context).tabBarTheme.labelColor,
                  size: 40,
                ).paddingOnly(bottom: 10),
                Text(
                  translate(
                    _emptyMessages[widget.peers.loadEvent] ?? 'Empty',
                  ),
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Theme.of(context).tabBarTheme.labelColor,
                  ),
                ),
              ],
            ),
          );""",
        """          return _buildActionableEmptyState(context);""",
        "Replace bare empty state with actionable personal empty state",
    )

    pvtxt = replace_exact(
        pvtxt,
        """            // We should avoid too many rebuilds. Win10(Some machines) on Flutter 3.19.6.
            // Continious rebuilds of `ListView.builder` will cause memory leak.
            // Simple demo can reproduce this issue.
            final Widget child = Obx(() => stateGlobal.isPortrait.isTrue""",
        """            if (peers.isEmpty) {
              return _buildNoMatchEmptyState(context);
            }

            // We should avoid too many rebuilds. Win10(Some machines) on Flutter 3.19.6.
            // Continious rebuilds of `ListView.builder` will cause memory leak.
            // Simple demo can reproduce this issue.
            final Widget child = Obx(() => stateGlobal.isPortrait.isTrue""",
        "Add actionable no-matching-devices filter empty state",
    )

    pvtxt = replace_exact(
        pvtxt,
        """    if (widget.peerFilter != null) {
      peers = peers.where((peer) => widget.peerFilter!(peer)).toList();
    }""",
        """    if (widget.peerFilter != null) {
      peers = peers.where((peer) => widget.peerFilter!(peer)).toList();
    }
    if (peerOnlineOnly.value == 'Y') {
      peers = peers.where((peer) => peer.online).toList();
    }""",
        "Apply Online-only filter inside matchPeers",
    )

    pvtxt = replace_exact(
        pvtxt,
        """  String _cardId(String id) => widget.peers.name + id;""",
        """  Widget _buildActionableEmptyState(BuildContext context) {
    final c = RrColors.of(context);
    final isFav = widget.peers.loadEvent == LoadEvent.favorite;
    final isLan = widget.peers.loadEvent == LoadEvent.lan;
    final String heading = isFav
        ? 'No pinned devices yet'
        : isLan
            ? 'No LAN devices found'
            : 'No recent devices yet';
    final String hint = isFav
        ? 'Star any device in Recent or LAN for 1-click access, or enter an ID above.'
        : isLan
            ? 'Make sure your other devices are running RRRemote on the same network.'
            : 'Enter a device ID above or pick a device on your local network.';
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 360),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: c.bgSubtle,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  isFav
                      ? Icons.star_outline_rounded
                      : isLan
                          ? Icons.lan_outlined
                          : Icons.devices_other_rounded,
                  size: 24,
                  color: c.textSecondary,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                heading,
                textAlign: TextAlign.center,
                style: RrText.title(c.textPrimary),
              ),
              const SizedBox(height: 6),
              Text(
                hint,
                textAlign: TextAlign.center,
                style: RrText.body(c.textSecondary),
              ),
              const SizedBox(height: 16),
              if (isFav)
                OutlinedButton(
                  onPressed: () {
                    gFFI.peerTabModel.setCurrentTab(PeerTabIndex.lan.index);
                    bind.setLocalFlutterOption(
                      k: kOptionPeerTabIndex,
                      v: PeerTabIndex.lan.index.toString(),
                    );
                  },
                  child: const Text('Browse LAN devices'),
                )
              else if (isLan)
                OutlinedButton(
                  onPressed: () {
                    bind.mainDiscover();
                    bind.mainLoadLanPeers();
                  },
                  child: const Text('Scan local network'),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildNoMatchEmptyState(BuildContext context) {
    final c = RrColors.of(context);
    final q = peerSearchText.value.trim();
    final onlineOnly = peerOnlineOnly.value == 'Y';
    final title = q.isNotEmpty
        ? "No devices match '$q'"
        : onlineOnly
            ? 'No online devices right now'
            : 'No devices found';
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 340),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.filter_list_off_rounded,
                  size: 32, color: c.textSecondary),
              const SizedBox(height: 10),
              Text(
                title,
                textAlign: TextAlign.center,
                style: RrText.label(c.textPrimary, weight: FontWeight.w600),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () {
                  peerSearchTextController.clear();
                  peerSearchText.value = '';
                  peerOnlineOnly.value = '';
                },
                child: const Text('Clear filters'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _cardId(String id) => widget.peers.name + id;""",
        "Add actionable empty state and filtered no-match state builders",
    )
    write_text(pv_p, pvtxt)

    # ------------------------------------------------------------------
    # 4. peer_card.dart: 1-click connect, keyboard Focus + Enter, RenderBox menu,
    #    non-color-only Online/Offline indicator, image inset outline
    # ------------------------------------------------------------------
    card_p = root / "flutter" / "lib" / "common" / "widgets" / "peer_card.dart"
    ctxt = read_text(card_p)

    ctxt = replace_exact(
        ctxt,
        """  final double _cardRadius = 16;
  final double _tileRadius = 5;
  final double _borderWidth = 2;""",
        """  final double _cardRadius = 12;
  final double _tileRadius = 8;
  final double _borderWidth = 2.0;
  final RxBool _isHovered = false.obs;
  final RxBool _isFocused = false.obs;""",
        "PeerCard radii, hover, and focus state",
    )

    # 1-click connect on Desktop (when not in multi-selection mode)
    ctxt = replace_exact(
        ctxt,
        """        onTap: () {
          if (peerTabModel.multiSelectionMode) {
            peerTabModel.select(peer);
          } else {
            if (isMobile) {
              widget.connect(context, peer.id);
            } else {
              peerTabModel.select(peer);
            }
          }
        },""",
        """        onTap: () {
          if (peerTabModel.multiSelectionMode) {
            peerTabModel.select(peer);
          } else {
            widget.connect(context, peer.id);
          }
        },""",
        "1-click connect on Desktop & Mobile PeerCard",
    )

    # Keyboard-focusable PeerCard with visible 2px focusRing & Enter/Space activation
    ctxt = replace_exact(
        ctxt,
        """  Widget _buildLandscape() {
    final peer = super.widget.peer;
    var deco = Rx<BoxDecoration?>(
      BoxDecoration(
        border: Border.all(color: Colors.transparent, width: _borderWidth),
        borderRadius: BorderRadius.circular(
          peerCardUiType.value == PeerUiType.grid ? _cardRadius : _tileRadius,
        ),
      ),
    );
    return MouseRegion(
      onEnter: (evt) {
        deco.value = BoxDecoration(
          border: Border.all(
              color: Theme.of(context).colorScheme.primary,
              width: _borderWidth),
          borderRadius: BorderRadius.circular(
            peerCardUiType.value == PeerUiType.grid ? _cardRadius : _tileRadius,
          ),
        );
      },
      onExit: (evt) {
        deco.value = BoxDecoration(
          border: Border.all(color: Colors.transparent, width: _borderWidth),
          borderRadius: BorderRadius.circular(
            peerCardUiType.value == PeerUiType.grid ? _cardRadius : _tileRadius,
          ),
        );
      },
      child: gestureDetector(
          child: Obx(() => peerCardUiType.value == PeerUiType.grid
              ? _buildPeerCard(context, peer, deco)
              : _buildPeerTile(context, peer, deco))),
    );
  }""",
        """  BoxDecoration _cardBorderDecoration(BuildContext context) {
    final c = RrColors.of(context);
    final radius =
        peerCardUiType.value == PeerUiType.grid ? _cardRadius : _tileRadius;
    if (_isFocused.value) {
      return BoxDecoration(
        border: Border.all(color: c.focusRing, width: _borderWidth),
        borderRadius: BorderRadius.circular(radius),
      );
    }
    if (_isHovered.value) {
      return BoxDecoration(
        border: Border.all(color: c.accentSolid, width: 1.5),
        borderRadius: BorderRadius.circular(radius),
      );
    }
    return BoxDecoration(
      border: Border.all(color: c.borderSubtle, width: 1.0),
      borderRadius: BorderRadius.circular(radius),
    );
  }

  Widget _buildLandscape() {
    final peer = super.widget.peer;
    final deco = Rx<BoxDecoration?>(_cardBorderDecoration(context));
    void syncDeco() {
      deco.value = _cardBorderDecoration(context);
    }

    final displayName =
        peer.alias.isEmpty ? formatID(peer.id) : peer.alias;
    final statusWord = translate(peer.online ? 'Online' : 'Offline');
    return Semantics(
      button: true,
      label: '$displayName, $statusWord. ${translate('Connect')}',
      child: Focus(
        onFocusChange: (focused) {
          _isFocused.value = focused;
          syncDeco();
        },
        onKeyEvent: (node, event) {
          if (event is KeyDownEvent &&
              (event.logicalKey == LogicalKeyboardKey.enter ||
                  event.logicalKey == LogicalKeyboardKey.numpadEnter ||
                  event.logicalKey == LogicalKeyboardKey.space)) {
            widget.connect(context, peer.id);
            return KeyEventResult.handled;
          }
          return KeyEventResult.ignored;
        },
        child: MouseRegion(
          cursor: SystemMouseCursors.click,
          onEnter: (_) {
            _isHovered.value = true;
            syncDeco();
          },
          onExit: (_) {
            _isHovered.value = false;
            syncDeco();
          },
          child: gestureDetector(
              child: Obx(() => peerCardUiType.value == PeerUiType.grid
                  ? _buildPeerCard(context, peer, deco)
                  : _buildPeerTile(context, peer, deco))),
        ),
      ),
    );
  }""",
        "Focusable keyboard-accessible PeerCard with Enter/Space connect & 2px focus ring",
    )

    # Clean hostname · platform subtitle + 12px AA secondary style + image inset outline
    ctxt = replace_exact(
        ctxt,
        """  makeChild(bool isPortrait, Peer peer) {
    final name = hideUsernameOnCard == true
        ? peer.hostname
        : '${peer.username}${peer.username.isNotEmpty && peer.hostname.isNotEmpty ? '@' : ''}${peer.hostname}';
    final greyStyle = TextStyle(
        fontSize: 11,
        color: Theme.of(context).textTheme.titleLarge?.color?.withOpacity(0.6));""",
        """  String _formatSubtitle(Peer peer) {
    final host = peer.hostname.trim().isNotEmpty
        ? peer.hostname.trim()
        : peer.username.trim();
    final plat = peer.platform.trim();
    if (host.isNotEmpty && plat.isNotEmpty) {
      return '$host · $plat';
    }
    return host.isNotEmpty ? host : plat;
  }

  makeChild(bool isPortrait, Peer peer) {
    final c = RrColors.of(context);
    final name = _formatSubtitle(peer);
    final greyStyle = RrText.caption(c.textSecondary, weight: FontWeight.w400);""",
        "Clean hostname · platform subtitle with 12px AA secondary style",
    )

    ctxt = replace_exact(
        ctxt,
        """  Widget _buildPeerCard(
      BuildContext context, Peer peer, Rx<BoxDecoration?> deco) {
    hideUsernameOnCard ??=
        bind.mainGetBuildinOption(key: kHideUsernameOnCard) == 'Y';
    final name = hideUsernameOnCard == true
        ? peer.hostname
        : '${peer.username}${peer.username.isNotEmpty && peer.hostname.isNotEmpty ? '@' : ''}${peer.hostname}';""",
        """  Widget _buildPeerCard(
      BuildContext context, Peer peer, Rx<BoxDecoration?> deco) {
    final name = _formatSubtitle(peer);""",
        "Clean hostname · platform subtitle on PeerCard grid",
    )

    # Add subtle 1px image inset outline on thumbnail container & accessible white text
    ctxt = replace_exact(
        ctxt,
        """                Expanded(
                  child: Container(
                    color: str2color('${peer.id}${peer.platform}', 0x7f),""",
        """                Expanded(
                  child: Container(
                    decoration: BoxDecoration(
                      color: str2color('${peer.id}${peer.platform}', 0xF2),
                      border: Border(
                        bottom: BorderSide(
                          color: RrColors.of(context).imageOutline,
                          width: 1,
                        ),
                      ),
                    ),""",
        "PeerCard thumbnail surface with pure black/white 10% inset edge",
    )

    # Accessible 1-click Connect pill visible on hover OR focus, optically aligned play triangle
    ctxt = replace_exact(
        ctxt,
        """        if (colors.isNotEmpty)
          Positioned(
            top: 4,
            right: 12,
            child: CustomPaint(
              painter: TagPainter(radius: 4, colors: colors),
            ),
          )
      ]),""",
        """        if (colors.isNotEmpty)
          Positioned(
            top: 4,
            right: 12,
            child: CustomPaint(
              painter: TagPainter(radius: 4, colors: colors),
            ),
          ),
        if (isDesktop || isWebDesktop)
          Obx(() => (_isHovered.value || _isFocused.value)
              ? Positioned(
                  bottom: 44,
                  right: 10,
                  child: Material(
                    color: RrColors.of(context).accentSolid,
                    borderRadius: BorderRadius.circular(8),
                    elevation: 2,
                    child: InkWell(
                      borderRadius: BorderRadius.circular(8),
                      onTap: () => widget.connect(context, peer.id),
                      child: Padding(
                        padding: const EdgeInsetsDirectional.fromSTEB(
                            8, 5, 10, 5),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Transform.translate(
                              offset: const Offset(1.0, 0),
                              child: const Icon(Icons.play_arrow_rounded,
                                  size: 15, color: Colors.white),
                            ),
                            const SizedBox(width: 3),
                            Text(
                              translate('Connect'),
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                )
              : const SizedBox.shrink()),
      ]),""",
        "Hover-or-focus 1-click Connect button with optical triangle nudge & 12px text",
    )

    # Make desktop _actionMore keyboard-accessible & RenderBox-anchored (replaces raw Listener)
    ctxt = replace_exact(
        ctxt,
        """  Widget _actionMore(Peer peer) => Listener(
      onPointerDown: (e) {
        final x = e.position.dx;
        final y = e.position.dy;
        _menuPos = RelativeRect.fromLTRB(x, y, x, y);
      },
      onPointerUp: (_) => _showPeerMenu(peer.id),
      child: build_more(context));""",
        """  Widget _actionMore(Peer peer) {
    final label = peer.alias.isEmpty ? formatID(peer.id) : peer.alias;
    return Semantics(
      container: true,
      button: true,
      label: '${translate('More')} ($label)',
      child: Tooltip(
        message: translate('More'),
        child: Builder(
          builder: (btnCtx) => build_more(btnCtx, onTap: () {
            final box = btnCtx.findRenderObject() as RenderBox?;
            final pos = box != null
                ? box.localToGlobal(box.size.center(Offset.zero))
                : const Offset(0, 0);
            _menuPos =
                RelativeRect.fromLTRB(pos.dx, pos.dy, pos.dx, pos.dy);
            _showPeerMenu(peer.id);
          }),
        ),
      ),
    );
  }""",
        "Keyboard-focusable RenderBox-anchored PeerCard overflow menu",
    )

    # Remove stranger 'Request approval' submenu from PeerCard context menu
    ctxt = replace_exact(
        ctxt,
        """    menuItems.add(MenuEntryDivider<String>());
    menuItems.add(_requestApprovalAction(context));
    // menuItems.add(await _openNewConnInOptAction(peer.id));""",
        """    if (!isWeb) {
      menuItems.add(MenuEntryDivider<String>());
    }""",
        "Remove stranger Request Approval submenu from PeerCard context menu",
    )

    # Non-color-only Online/Offline indicator: solid green dot (online) vs hollow slate ring (offline)
    ctxt = replace_exact(
        ctxt,
        """Widget getOnline(double rightPadding, bool online) {
  return Tooltip(
      message: translate(online ? 'Online' : 'Offline'),
      waitDuration: const Duration(seconds: 1),
      child: Padding(
          padding: EdgeInsets.fromLTRB(0, 4, rightPadding, 4),
          child: CircleAvatar(
              radius: 3, backgroundColor: online ? Colors.green : kColorWarn)));
}""",
        """Widget getOnline(double rightPadding, bool online) {
  return Builder(
    builder: (context) {
      final c = RrColors.of(context);
      final label = translate(online ? 'Online' : 'Offline');
      return Semantics(
        label: label,
        child: Tooltip(
          message: label,
          waitDuration: const Duration(milliseconds: 500),
          child: Padding(
            padding: EdgeInsetsDirectional.fromSTEB(0, 4, rightPadding, 4),
            child: Container(
              width: 9,
              height: 9,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: online ? c.successSolid : Colors.transparent,
                border: online
                    ? null
                    : Border.all(color: c.offlineSolid, width: 1.75),
              ),
            ),
          ),
        ),
      );
    },
  );
}""",
        "Non-color-only shape+color Online/Offline indicator (AA >= 4.76:1)",
    )

    # Upgrade build_more target size to 32x32px with crisp RrColors hover
    ctxt = replace_exact(
        ctxt,
        """  final button = InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap ?? () {},
      onHover: (value) => hover.value = value,
      child: Obx(() => CircleAvatar(
          radius: 14,
          backgroundColor: hover.value
              ? (invert
                  ? Theme.of(context).colorScheme.background
                  : Theme.of(context).scaffoldBackgroundColor)
              : (invert
                  ? Theme.of(context).scaffoldBackgroundColor
                  : Theme.of(context).colorScheme.background),
          child: Icon(Icons.more_vert,
              size: 18,
              color: hover.value
                  ? Theme.of(context).textTheme.titleLarge?.color
                  : Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.color
                      ?.withOpacity(0.5)))));""",
        """  final c = RrColors.of(context);
  final button = InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap ?? () {},
      onHover: (value) => hover.value = value,
      child: Obx(() => Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(8),
            color: hover.value ? c.bgHover : Colors.transparent,
          ),
          child: Icon(Icons.more_vert_rounded,
              size: 18,
              color: hover.value ? c.textPrimary : c.textSecondary))));""",
        "Accessible 32x32px PeerCard overflow icon button",
    )

    write_text(card_p, ctxt)
