// network/server.go
package network

import (
	"encoding/json"
	"fmt"
	"net/http"
	"orbit_node/core"
        "time"
        "strings"
)

func StartHTTPServer(n *core.OrbitNode) {
	http.HandleFunc("/api/chain", func(w http.ResponseWriter, r *http.Request) {
		n.ChainMu.RLock()
		defer n.ChainMu.RUnlock()
		json.NewEncoder(w).Encode(n.Chain)
	})

	http.HandleFunc("/receive_block", func(w http.ResponseWriter, r *http.Request) {
		var block core.Block
		_ = json.NewDecoder(r.Body).Decode(&block)
		if n.ValidateBlock(block) {
			n.Chain = append(n.Chain, block)
			n.SaveChain()
			w.WriteHeader(http.StatusOK)
		} else {
			http.Error(w, "Invalid block", http.StatusBadRequest)
		}
	})

	addr := fmt.Sprintf(":%d", n.Port)
	http.ListenAndServe(addr, nil)
}

func DisplayStats(n *core.OrbitNode) {
	for n.Running {
		n.NodesMu.RLock()
		uptime := n.Nodes[n.NodeID]["uptime"].(float64)
		trust := n.Nodes[n.NodeID]["trust"].(float64)
		n.NodesMu.RUnlock()

		fmt.Print("\033[H\033[2J")
		fmt.Println("🔗 Orbit Node Dashboard")
		fmt.Println(strings.Repeat("=", 40))
		fmt.Printf("Node ID   : %s\n", n.NodeID)
		fmt.Printf("Address   : %s\n", n.Address)
		fmt.Printf("Port      : %d\n", n.Port)
		fmt.Printf("Trust     : %.4f\n", trust)
		fmt.Printf("Uptime    : %.4f\n", uptime)
                fmt.Printf("Valid    : %d\n", n.Valid)
		fmt.Printf("Chain Len : %d blocks\n", len(n.Chain))
		time.Sleep(10 * time.Second)
	}
}
