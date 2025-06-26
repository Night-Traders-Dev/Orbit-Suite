// core/sync.go
package core

import (
	"bytes"
	"encoding/json"
	"log"
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
		"host":      host,
		"port":      n.Port,
		"uptime":    1.0,
		"trust":     1.0,
		"last_seen": time.Now().Unix(),
		"users":     []string{n.Address},
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
		log.Println("[ERROR] Could not fetch chain:", err)
		return
	}
	defer resp.Body.Close()
	var remote []Block
	err = json.NewDecoder(resp.Body).Decode(&remote)
	if err != nil {
		log.Println("[ERROR] Invalid chain JSON:", err)
		return
	}
	if len(remote) > len(n.Chain) {
		n.Chain = remote
		n.SaveChain()
		log.Println("[SYNC] Chain updated from explorer.")
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
