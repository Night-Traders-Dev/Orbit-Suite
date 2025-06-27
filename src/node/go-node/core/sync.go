// core/sync.go
package core

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "time"
)

const (
    ApiURL      = "https://amateur-eric-receptors-casa.trycloudflare.com/"
    NodePing    = ApiURL + "node_ping"
    ApiChain    = ApiURL + "api/chain"
	ApiBalance  = ApiURL + "api/balance/"
	// NodeFeeCollector is the address of the ORB node fee collector.
    orbAddress  = "ORB.3C0738F00DE16991DDD5B506"
    timeoutSecs = 5 * time.Second
)

// BalanceResponse models the JSON returned by GET /api/balance/<address>
type BalanceResponse struct {
    Total     uint64 `json:"total_balance"`
    Available uint64 `json:"available_balance"`
    Locked    uint64 `json:"locked_balance"`
}

// GetBalance fetches and decodes balance for the given ORB address.
func GetBalance(address string) (*BalanceResponse, error) {
    endpoint := ApiBalance + address
    client := &http.Client{Timeout: timeoutSecs}
    resp, err := client.Get(endpoint)
    if err != nil {
        return nil, fmt.Errorf("GET %s failed: %w", endpoint, err)
    }
    defer resp.Body.Close()

    if resp.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(resp.Body)
        return nil, fmt.Errorf("unexpected status %s: %s", resp.Status, string(body))
    }

    var bal BalanceResponse
    if err := json.NewDecoder(resp.Body).Decode(&bal); err != nil {
        return nil, fmt.Errorf("invalid balance JSON: %w", err)
    }
    return &bal, nil
}

// GetORBBalance is a convenience wrapper for the well-known ORB address.
func GetORBBalance() (*BalanceResponse, error) {
    return GetBalance(orbAddress)
}

func (n *OrbitNode) RegisterNode() {
    host := n.TunnelURL
    if host == "" {
        host = "127.0.0.1"
    }
    // Fetch ORB balance and handle error
    orbBal, err := GetORBBalance()
    var nodeFeeBalance uint64
    if err == nil && orbBal != nil {
        nodeFeeBalance = orbBal.total_balance
    } else {
        nodeFeeBalance = 0
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
        "nodefeebalance": nodeFeeBalance,
    }
    n.SaveNodes()

    payload, err := json.Marshal(n.Nodes[n.NodeID])
    if err == nil {
        http.Post(NodePing, "application/json", bytes.NewReader(payload))
    }
}

func (n *OrbitNode) SyncWithExplorer() {
    resp, err := http.Get(ApiChain)
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