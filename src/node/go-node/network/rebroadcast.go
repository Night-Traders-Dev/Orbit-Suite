// network/rebroadcast.go
package network

import (
	"encoding/json"
	"log"
	"net/http"
	"orbit_node/core"
	"time"
)

func RebroadcastIfNeeded(n *core.OrbitNode) {
	for n.Running {
		resp, err := http.Get("https://oliver-butler-oasis-builder.trycloudflare.com/active_nodes")
		if err != nil {
			time.Sleep(30 * time.Second)
			continue
		}
		var active map[string]interface{}
		_ = json.NewDecoder(resp.Body).Decode(&active)
		resp.Body.Close()
		if _, exists := active[n.NodeID]; !exists {
			log.Println("[REBROADCAST] Node not found in active_nodes. Re-registering...")
			n.RegisterNode()
		}
		time.Sleep(30 * time.Second)
	}
}

func PollForNewBlocks(n *core.OrbitNode) {
	for n.Running {
		n.SyncWithExplorer()
		time.Sleep(15 * time.Second)
	}
}
