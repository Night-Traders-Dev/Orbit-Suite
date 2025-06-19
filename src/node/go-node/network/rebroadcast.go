//network/rebroadcast.go:
package network

import (
	"encoding/json"
	"io"
	"log"
	"net/http"
	"orbit_node/core"
	"time"
)

func RebroadcastIfNeeded(n *core.OrbitNode) {
	for n.Running {
		if !isNodeActive(n) {
			log.Println("[RE-REGISTER] Node not in active_nodes, rebroadcasting")
			core.RegisterNode(n)
		}
		time.Sleep(30 * time.Second)
	}
}

func isNodeActive(n *core.OrbitNode) bool {
	resp, err := http.Get(core.ExplorerURL + "/active_nodes")
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	var active map[string]interface{}
	body, _ := io.ReadAll(resp.Body)
	err = json.Unmarshal(body, &active)
	if err != nil {
		return false
	}
	_, exists := active[n.NodeID]
	return exists
}
