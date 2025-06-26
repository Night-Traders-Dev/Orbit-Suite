// core/ui.go
package core

import (
	"fmt"
	"time"

	"github.com/rivo/tview"
)

type TUI struct {
	app      *tview.Application
	layout   *tview.Flex
	textView *tview.TextView
	node *OrbitNode
}

func StartTUI(node *OrbitNode) {
	tui := &TUI{
		app:      tview.NewApplication(),
		textView: tview.NewTextView().SetDynamicColors(true).SetScrollable(true).SetWrap(true),
		node:     node,
	}

	tui.textView.SetBorder(true).SetTitle(" Orbit Node Dashboard ")

	tui.layout = tview.NewFlex().SetDirection(tview.FlexRow).
		AddItem(tview.NewTextView().SetText("[::b]Orbit Node Console UI").SetTextAlign(tview.AlignCenter), 1, 0, false).
		AddItem(tui.textView, 0, 1, true)

	tui.app.SetRoot(tui.layout, true)

	go tui.updateLoop()

	if err := tui.app.Run(); err != nil {
		panic(err)
	}
}

func (t *TUI) updateLoop() {
	for t.node.Running {
		t.app.QueueUpdateDraw(func() {
			content := t.renderDashboard()
			t.textView.SetText(content)
		})
		time.Sleep(5 * time.Second)
	}
}

func (t *TUI) renderDashboard() string {
	header := "[blue]================ Orbit Node Dashboard ================[-]"

	summary := fmt.Sprintf(`
[green]Node ID     :[-] %s
[green]Orbit Address:[-] %s
[green]Port        :[-] %d
[green]Tunnel URL  :[-] %s
[green]Chain Length:[-] %d
[green]Block Height:[-] %d
`,
		t.node.NodeID,
		t.node.Address,
		t.node.Port,
		t.node.TunnelURL,
		len(t.node.Chain),
		t.node.BlockHeight)

	latestBlocks := "[yellow]Recent Blocks:[-]"
	limit := 10
	if len(t.node.Chain) < 10 {
		limit = len(t.node.Chain)
	}
	for i := len(t.node.Chain) - 1; i >= len(t.node.Chain)-limit; i-- {
		block := t.node.Chain[i]
		timeStr := time.Unix(block.Timestamp, 0).Format("15:04:05")
		latestBlocks += fmt.Sprintf("\n[#87cefa]#%d Hash:[-] %s [gray]Time:[-] %s", block.Index, block.Hash[:8], timeStr)
	}

	footer := fmt.Sprintf("\n[gray]%s UI started. Press Ctrl+C to exit.[-]", time.Now().Format("15:04:05"))

	return fmt.Sprintf("%s\n%s\n%s\n%s", header, summary, latestBlocks, footer)
}
