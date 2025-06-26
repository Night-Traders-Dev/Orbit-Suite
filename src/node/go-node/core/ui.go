package core

import (
	"fmt"
	"strings"
	"time"

	"github.com/gdamore/tcell/v2"
	"github.com/rivo/tview"
)

// StartTUI launches a terminal UI for the given OrbitNode.
func StartTUI(node *OrbitNode) {
	app := tview.NewApplication()

	// Header banner
	header := tview.NewTextView().
		SetTextAlign(tview.AlignCenter).
		SetDynamicColors(true).
		SetText("[::b]🌐 Orbit Node Console UI")

	// Node info & chain view, no wrap, auto-scroll back to top
	nodeInfo := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(false)
	chainView := tview.NewTextView().
		SetDynamicColors(true).
		SetWrap(false)

	// Pages container (in case you want to layer more views later)
	pages := tview.NewPages()
	detailed := false

	updateNodeInfo := func() {
		// Build the full text in one go:
		text := fmt.Sprintf(
			`[blue]Node ID       : [white]%s
[blue]Orbit Address : [white]%s
[blue]Port          : [white]%d
[blue]Tunnel        : [white]%s
[blue]Chain Length  : [white]%d`,
			node.NodeID, node.Address, node.Port, node.TunnelURL, len(node.Chain),
		)

		// Replace the buffer and reset scroll
		nodeInfo.SetText(text)
		nodeInfo.ScrollToBeginning()
	}

	updateChainView := func() {
		node.ChainMu.RLock()
		defer node.ChainMu.RUnlock()

		// Accumulate lines in a slice
		lines := []string{fmt.Sprintf("[green]Block Height: %d", len(node.Chain))}
		limit := 5
		if detailed {
			limit = 15
		}
		for i := len(node.Chain) - 1; i >= 0 && i > len(node.Chain)-1-limit; i-- {
			block := node.Chain[i]
			hash, _ := block["hash"].(string)
			ts, _ := block["timestamp"].(float64)
			timeStr := time.Unix(int64(ts), 0).Format("15:04:05")
			lines = append(lines,
				fmt.Sprintf("[yellow]#%d [white]Hash: %s [blue]Time: %s",
					i, hash[:8], timeStr,
				),
			)
		}

		// Join, set text, reset scroll
		chainView.SetText(strings.Join(lines, "\n"))
		chainView.ScrollToBeginning()
	}

	// Layout: header, then two-column split of nodeInfo | chainView
	left := tview.NewFlex().SetDirection(tview.FlexRow).
		AddItem(nodeInfo, 0, 1, false).
		AddItem(chainView, 0, 3, false)

	mainFlex := tview.NewFlex().
		AddItem(left, 0, 3, true)

	root := tview.NewFlex().SetDirection(tview.FlexRow).
		AddItem(header, 1, 1, false).
		AddItem(mainFlex, 0, 1, true)

	pages.AddPage("main", root, true, true)

	// Combined update
	updateAll := func() {
		app.QueueUpdateDraw(func() {
			updateNodeInfo()
			updateChainView()
		})
	}

	// Refresh loop
	go func() {
		for node.Running {
			updateAll()
			time.Sleep(5 * time.Second)
		}
	}()

	// Keybindings
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

	// Start
	if err := app.
		SetRoot(pages, true).
		EnableMouse(true).
		Run(); err != nil {
		panic(err)
	}
}