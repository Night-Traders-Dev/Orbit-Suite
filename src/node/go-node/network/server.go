// network/server.go
package network

import (
	"encoding/json"
	"fmt"
	"net/http"
	"orbit_node/core"
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

