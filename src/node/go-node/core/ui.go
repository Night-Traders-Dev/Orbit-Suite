package core

import (
	"fmt"
	"time"

	"github.com/rivo/tview"
	"github.com/gdamore/tcell/v2"
)

func StartTUI(node *OrbitNode) {
	app := tview.NewApplication()

	header := tview.NewTextView().
		SetTextAlign(tview.AlignCenter).
		SetDynamicColors(true).
		SetText("[::b]🌐 Orbit Node Console UI")

	nodeInfo := tview.NewTextView().SetDynamicColors(true).SetWrap(false)
	chainView := tview.NewTextView().SetDynamicColors(true).SetWrap(false)


	pages := tview.NewPages()
	detailed := false

	updateNodeInfo := func() {
		nodeInfo.Clear()
		fmt.Fprintf(nodeInfo, `
[blue]Node ID       : [white]%s
[blue]Orbit Address : [white]%s
[blue]Port          : [white]%d
[blue]Tunnel        : [white]%s
[blue]Chain Length  : [white]%d
`,
			node.NodeID, node.Address, node.Port, node.TunnelURL, len(node.Chain))
	}

	updateChainView := func() {
		node.ChainMu.RLock()
		defer node.ChainMu.RUnlock()
		chainView.Clear()
		fmt.Fprintf(chainView, "[green]Block Height: %d\n", len(node.Chain))
		count := 5
		if detailed {
			count = 15
		}
		for i := len(node.Chain) - 1; i >= 0 && i > len(node.Chain)-1-count; i-- {
			block := node.Chain[i]
			hash, _ := block["hash"].(string)
			timestamp, _ := block["timestamp"].(float64)
			fmt.Fprintf(chainView, "[yellow]#%d [white]Hash: %s [blue]Time: %s\n",
				i, hash[:8], time.Unix(int64(timestamp), 0).Format("15:04:05"))
		}
	}


	left := tview.NewFlex().SetDirection(tview.FlexRow).
		AddItem(nodeInfo, 0, 1, false).
		AddItem(chainView, 0, 3, false)

	mainFlex := tview.NewFlex().
		AddItem(left, 0, 3, true).
	flex := tview.NewFlex().SetDirection(tview.FlexRow).
		AddItem(header, 1, 1, false).
		AddItem(mainFlex, 0, 1, true)

	pages.AddPage("main", flex, true, true)

	updateAll := func() {
		app.QueueUpdateDraw(func() {
			updateNodeInfo()
			updateChainView()
		})
	}

	go func() {
		for node.Running {
			updateAll()
			time.Sleep(5 * time.Second)
		}
	}()

	app.SetInputCapture(func(event *tcell.EventKey) *tcell.EventKey {
		switch event.Rune() {
		case 'r':
			updateAll()
		case 'd':
			detailed = !detailed
			updateAll()
		}
		return event
	})

	if err := app.SetRoot(pages, true).EnableMouse(true).Run(); err != nil {
		panic(err)
	}
}
