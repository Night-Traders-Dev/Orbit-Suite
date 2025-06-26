package core

import (
	"fmt"
	"time"

	"github.com/rivo/tview"
)

// StartTUI launches a terminal UI for the given OrbitNode.
func StartTUI(node *OrbitNode) {
	app := tview.NewApplication()

	header := tview.NewTextView().
		SetTextAlign(tview.AlignCenter).
		SetDynamicColors(true).
		SetText("[::b]🌐 Orbit Node Console UI")

	nodeInfo := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(false)

	chainView := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(false)

	logView := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(false)

	updateNodeInfo := func() {
		nodeInfo.Clear()
		fmt.Fprintf(nodeInfo, `
[blue]Node ID       : [white]%s
[blue]Orbit Address : [white]%s
[blue]Port          : [white]%d
[blue]Tunnel        : [white]%s
[blue]Chain Length  : [white]%d
`,
			node.NodeID,
			node.Address,
			node.Port,
			node.TunnelURL,
			len(node.Chain),
		)
	}

	updateChainView := func() {
		node.ChainMu.RLock()
		defer node.ChainMu.RUnlock()

		chainView.Clear()
		fmt.Fprintf(chainView, "[green]Block Height: %d\n", len(node.Chain))
		for i := len(node.Chain) - 1; i >= 0 && i > len(node.Chain)-6; i-- {
			block := node.Chain[i]
			hash, _ := block["hash"].(string)
			timestamp, _ := block["timestamp"].(float64)
			fmt.Fprintf(
				chainView,
				"[yellow]#%d [white]Hash: %s [blue]Time: %s\n",
				i,
				hash[:8],
				time.Unix(int64(timestamp), 0).Format("15:04:05"),
			)
		}
	}

	updateLog := func(msg string) {
		fmt.Fprintf(logView, "[gray]%s [white]%s\n", time.Now().Format("15:04:05"), msg)
	}

	mainFlex := tview.NewFlex().SetDirection(tview.FlexRow).
		AddItem(header, 1, 1, false).
		AddItem(nodeInfo, 0, 1, false).
		AddItem(
			tview.NewFlex().
				AddItem(chainView, 0, 2, false).
				AddItem(logView, 0, 1, false),
			0, 3, true,
		)

	// Wrap in Pages to ensure full screen resizing works
	pages := tview.NewPages().
		AddPage("main", mainFlex, true, true)

	go func() {
		for node.Running {
			app.QueueUpdateDraw(func() {
				updateNodeInfo()
				updateChainView()
			})
			time.Sleep(5 * time.Second)
		}
	}()

	updateLog("UI started. Press Ctrl+C to exit.")

	if err := app.SetRoot(pages, true).EnableMouse(true).Run(); err != nil {
		panic(err)
	}
}
