package core

import (
	"fmt"
	"time"

	"github.com/rivo/tview"
)

// StartTUI launches a terminal UI for the given OrbitNode.
func StartTUI(node *OrbitNode) {
	app := tview.NewApplication()

	// header banner
	header := tview.NewTextView().
		SetTextAlign(tview.AlignCenter).
		SetText("🌐 Orbit Node Console UI")

	// node info: no wrap, horizontal scroll enabled
	nodeInfo := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(false).
		SetScrollable(true)

	// chain view: vertical scroll only, wrap off
	chainView := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(false).
		SetChangedFunc(func() { app.Draw() })

	// log view: no wrap, horizontal scroll enabled
	logView := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(false).
		SetScrollable(true).
		SetChangedFunc(func() { app.Draw() })

	// initialize the nodeInfo text
	nodeInfo.SetText(fmt.Sprintf(
		`[blue]Node ID: [white]%s
[blue]Orbit Address: [white]%s
[blue]Port: [white]%d
[blue]Tunnel: [white]%s
[blue]Chain Length: [white]%d`,
		node.NodeID,
		node.Address,
		node.Port,
		node.TunnelURL,
		len(node.Chain),
	))

	// function to update the chain view periodically
	updateChainView := func() {
		node.ChainMu.RLock()
		defer node.ChainMu.RUnlock()

		chainView.Clear()
		fmt.Fprintf(chainView, "[green]Block Height: %d\n", len(node.Chain))
		for i := len(node.Chain) - 1; i >= 0 && i > len(node.Chain)-6; i-- {
			blk := node.Chain[i]
			hash, _ := blk["hash"].(string)
			timestamp, _ := blk["timestamp"].(float64)
			fmt.Fprintf(
				chainView,
				"[yellow]#%d [white]Hash: %s [blue]Time: %s\n",
				i,
				hash[:8],
				time.Unix(int64(timestamp), 0).Format("15:04:05"),
			)
		}
	}



	// layout: header, nodeInfo, then a horizontal split of chainView | logView
	flex := tview.NewFlex().
		SetDirection(tview.FlexRow).
		AddItem(header, 1, 1, false).
		AddItem(nodeInfo, 6, 1, false).
		AddItem(
			tview.NewFlex().
				AddItem(chainView, 0, 2, false).
				AddItem(logView, 0, 1, false),
			0, 3, false,
		)

	// background refresh loop for the chain view
	go func() {
		for node.Running {
			updateChainView()
			time.Sleep(10 * time.Second)
		}
	}()


	if err := app.
		SetRoot(flex, true).
		EnableMouse(true).
		Run(); err != nil {
		panic(err)
	}
}