package core

import (
    "fmt"
    "strings"
    "time"

    "github.com/gdamore/tcell/v2"
    "github.com/rivo/tview"
)

// --------------------------------------------------------------------
// Exposed API for other modules
// --------------------------------------------------------------------

// Notify prints a one‐line message to the TUI’s status bar for the given duration.
// Safe to call from any goroutine.
func Notify(msg string, timeout time.Duration) {
    if notifyFunc != nil {
        notifyFunc(msg, timeout)
    }
}

// --------------------------------------------------------------------
// Internals: wiring up Notify → statusBar
// --------------------------------------------------------------------

var notifyFunc func(msg string, timeout time.Duration)

func StartTUI(node *OrbitNode) {
    app := tview.NewApplication()

    // Header banner
    header := tview.NewTextView().
        SetTextAlign(tview.AlignCenter).
        SetDynamicColors(true).
        SetText("[::b]🌐 Orbit Node Console UI")

    // Node info & chain view
    nodeInfo := tview.NewTextView().
        SetDynamicColors(true).
        SetWrap(false)
    chainView := tview.NewTextView().
        SetDynamicColors(true).
        SetWrap(false)

    // Status bar (one line at bottom)
    statusBar := tview.NewTextView().
        SetDynamicColors(true).
        SetTextAlign(tview.AlignCenter)

    // Pages container (in case you want to layer more views later)
    pages := tview.NewPages()
    detailed := false

    // ----------------------------------------------------------------
    // Functions to update the two main panes:
    // ----------------------------------------------------------------
    updateNodeInfo := func() {
        text := fmt.Sprintf(
            `[blue]Node ID       : [white]%s
[blue]User Address  : [white]%s
[blue]Orbit Address : [white]%s
[blue]Port          : [white]%d
[blue]Tunnel        : [white]%s
[blue]Valid         : [white]%d
[blue]Chain Length  : [white]%d`,
            node.NodeID, node.User, node.Address, node.Port,
            node.TunnelURL, node.Valid, len(node.Chain),
        )
        nodeInfo.SetText(text)
        nodeInfo.ScrollToBeginning()
    }

    updateChainView := func() {
        node.ChainMu.RLock()
        defer node.ChainMu.RUnlock()

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
        chainView.SetText(strings.Join(lines, "\n"))
        chainView.ScrollToBeginning()
    }

    // ----------------------------------------------------------------
    // Layout
    // ----------------------------------------------------------------
    left := tview.NewFlex().SetDirection(tview.FlexRow).
        AddItem(nodeInfo, 0, 1, false).
        AddItem(chainView, 0, 3, false)

    mainFlex := tview.NewFlex().
        AddItem(left, 0, 3, true)

    root := tview.NewFlex().SetDirection(tview.FlexRow).
        AddItem(header, 1, 1, false).
        AddItem(mainFlex, 0, 1, true).
        AddItem(statusBar, 1, 1, false)

    pages.AddPage("main", root, true, true)

    // ----------------------------------------------------------------
    // Notification plumbing
    // ----------------------------------------------------------------
    // This closure gets called by Notify(...)
    notifyFunc = func(msg string, timeout time.Duration) {
        // show message
        app.QueueUpdateDraw(func() {
            statusBar.SetText(fmt.Sprintf("[::b]%s", msg))
        })
        // clear after timeout
        go func() {
            time.Sleep(timeout)
            app.QueueUpdateDraw(func() {
                // only clear if it's the same message
                // (optional: you could skip this check)
                statusBar.SetText("")
            })
        }()
    }

    // ----------------------------------------------------------------
    // Combined update
    // ----------------------------------------------------------------
    updateAll := func() {
        app.QueueUpdateDraw(func() {
            updateNodeInfo()
            updateChainView()
        })
    }

    // ----------------------------------------------------------------
    // Refresh loop and keybindings
    // ----------------------------------------------------------------
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

    // ----------------------------------------------------------------
    // Start!
    // ----------------------------------------------------------------
    if err := app.
        SetRoot(pages, true).
        EnableMouse(true).
        Run(); err != nil {
        panic(err)
    }
}