//network/server.go:
package network

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"orbit_node/core"
//	"time"
)

func StartServer(n *core.OrbitNode) {
	http.HandleFunc("/api/chain", func(w http.ResponseWriter, r *http.Request) {
		n.ChainMu.RLock()
		defer n.ChainMu.RUnlock()
		json.NewEncoder(w).Encode(n.Chain)
	})

	http.HandleFunc("/receive_block", func(w http.ResponseWriter, r *http.Request) {
		var block core.Block
		err := json.NewDecoder(r.Body).Decode(&block)
		if err != nil {
			http.Error(w, "Invalid block", http.StatusBadRequest)
			return
		}
		n.Chain = append(n.Chain, block)
		core.SaveChain(n)
		w.WriteHeader(http.StatusOK)
	})

	log.Printf("[HTTP] Serving on :%d\n", n.Port)
	http.ListenAndServe(fmt.Sprintf(":%d", n.Port), nil)
}
