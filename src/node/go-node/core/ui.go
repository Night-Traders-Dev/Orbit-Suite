package core

import (
	"fmt"
	"strconv"
	"time"

	"github.com/rivo/tview"
	"github.com/gdamore/tcell/v2"
)

func StartTUI(node *OrbitNode) {
	app := tview.NewApplication()

	header := tview.NewTextView().
		SetTextAlign(tview.AlignCenter).
		SetText("🌐 Orbit Node Console UI")

	nodeInfo := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(true)

	chainView := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(false).
		SetChangedFunc(func() { app.Draw() })

	logView := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(true).
		SetChangedFunc(func() { app.Draw() })

	nodeInfo.SetText(fmt.Sprintf(`
[blue]Node ID: [white]%s
[blue]Orbit Address: [white]%s
[blue]Port: [white]%d
[blue]Tunnel: [white]%s
[blue]Chain Length: [white]%d
`,
		node.NodeID, node.Address, node.Port, node.TunnelURL, len(node.Chain)))

	updateChainView := func() {
		node.ChainMu.RLock()
		defer node.ChainMu.RUnlock()
		chainView.Clear()
		fmt.Fprintf(chainView, "[green]Block Height: %d\n", len(node.Chain))
		for i := len(node.Chain) - 1; i >= 0 && i > len(node.Chain)-6; i-- {
			blk := node.Chain[i]
			hash, _ := blk["hash"].(string)
			timestamp, _ := blk["timestamp"].(float64)
			fmt.Fprintf(chainView, "[yellow]#%d [white]Hash: %s [blue]Time: %s\n", i, hash[:8], time.Unix(int64(timestamp), 0).Format("15:04:05"))
		}
	}

	updateLog := func(msg string) {
		fmt.Fprintf(logView, "[gray]%s [white]%s\n", time.Now().Format("15:04:05"), msg)
	}

	flex := tview.NewFlex().SetDirection(tview.FlexRow).
		AddItem(header, 1, 1, false).
		AddItem(nodeInfo, 6, 1, false).
		AddItem(tview.NewFlex().AddItem(chainView, 0, 2, false).AddItem(logView, 0, 1, false), 0, 3, false)

	go func() {
		for node.Running {
			updateChainView()
			time.Sleep(10 * time.Second)
		}
	}()

	updateLog("UI started. Press Ctrl+C to exit.")

	if err := app.SetRoot(flex, true).EnableMouse(true).Run(); err != nil {
		panic(err)
	}
}
