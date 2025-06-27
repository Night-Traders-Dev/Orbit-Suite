// core/sync.go
package core

import (
	"bytes"
	"encoding/json"
	"net/http"
	"time"
)

func (n *OrbitNode) RegisterNode() {
	host := n.TunnelURL
	if host == "" {
		host = "127.0.0.1"
	}
	n.Nodes[n.NodeID] = map[string]interface{}{
		"id":        n.NodeID,
		"address":   n.Address,
		"user":      n.User,
		"host":      host,
		"port":      n.Port,
		"uptime":    1.0,
		"trust":     1.0,
		"last_seen": time.Now().Unix(),
		"users":     []string{n.User},
	}
	n.SaveNodes()

	payload, err := json.Marshal(n.Nodes[n.NodeID])
	if err == nil {
		http.Post("https://amateur-eric-receptors-casa.trycloudflare.com/node_ping", "application/json", bytes.NewReader(payload))
	}
}

func (n *OrbitNode) SyncWithExplorer() {
	resp, err := http.Get("https://amateur-eric-receptors-casa.trycloudflare.com/api/chain")
	if err != nil {
		Notify("[ERROR] Could not fetch chain:", 3*time.Second)
		return
	}
	defer resp.Body.Close()
	var remote []Block
	err = json.NewDecoder(resp.Body).Decode(&remote)
	if err != nil {
		Notify("[ERROR] Invalid chain JSON:", 3*time.Second)
		return
	}
	if len(remote) > len(n.Chain) {
		n.Chain = remote
		n.SaveChain()
		Notify("[SYNC] Chain updated from explorer.", 3*time.Second)
	}
}

func (n *OrbitNode) ValidateBlock(block map[string]interface{}) bool {
	if len(n.Chain) == 0 {
		return false
	}
	last := n.Chain[len(n.Chain)-1]
	if last["index"].(float64) == 0 {
		return true
	}
	if block["previous_hash"] != last["hash"] {
		return false
	}
        n.Valid += 1
	return true
}
