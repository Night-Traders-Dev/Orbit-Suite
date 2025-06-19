//core/sync.go:
package core

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"time"
)

const ExplorerURL = "https://oliver-butler-oasis-builder.trycloudflare.com"

func SyncWithExplorer(n *OrbitNode) {
	resp, err := http.Get(ExplorerURL + "/api/chain")
	if err != nil {
		log.Println("[SYNC] Explorer unavailable")
		return
	}
	defer resp.Body.Close()
	var remote []Block
	body, _ := io.ReadAll(resp.Body)
	err = json.Unmarshal(body, &remote)
	if err == nil && len(remote) > len(n.Chain) {
		n.Chain = remote
		SaveChain(n)
		log.Println("[SYNC] Chain updated from explorer")
	}
}

func RegisterNode(n *OrbitNode) {
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
	SaveNodes(n)

	payload, _ := json.Marshal(n.Nodes[n.NodeID])
	http.Post(ExplorerURL+"/node_ping", "application/json", bytes.NewReader(payload))
}
