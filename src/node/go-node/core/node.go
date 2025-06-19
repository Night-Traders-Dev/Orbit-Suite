// core/node.go
package core

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"math/rand"
	"net"
	"os"
	"path/filepath"
	"sync"
	"time"
        "net/http"
        "bytes"
)

type Block map[string]interface{}

type OrbitNode struct {
	Address   string
	Port      int
	NodeID    string
	TunnelURL string
	ChainFile string
	NodesFile string
        Valid     int
	Chain     []Block
	Nodes     map[string]map[string]interface{}
	ChainMu   sync.RWMutex
	NodesMu   sync.RWMutex
	Running   bool
}

const NodeDataDir = "node_data"

func NewOrbitNode(address string, port int, tunnelURL string) *OrbitNode {
	rand.Seed(time.Now().UnixNano())
	if port == 0 {
		port = getAvailablePort(5000, 5999)
	}
	os.MkdirAll(NodeDataDir, 0755)

	nodeID := fmt.Sprintf("Node%04d", rand.Intn(10000))
	nodesFile := filepath.Join(NodeDataDir, "nodes.json")
	chainFile := filepath.Join(NodeDataDir, fmt.Sprintf("orbit_chain.%s.json", nodeID))

	n := &OrbitNode{
		Address:   address,
		Port:      port,
		NodeID:    nodeID,
		TunnelURL: tunnelURL,
		NodesFile: nodesFile,
		ChainFile: chainFile,
		Nodes:     map[string]map[string]interface{}{},
		Chain:     []Block{},
		Running:   true,
	}

	n.LoadChain()
	n.LoadNodes()
	return n
}

func getAvailablePort(start, end int) int {
	for {
		port := rand.Intn(end-start+1) + start
		if !isPortInUse(port) {
			return port
		}
	}
}

func isPortInUse(port int) bool {
	ln, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return true
	}
	ln.Close()
	return false
}

func (n *OrbitNode) LoadNodes() {
	data, err := ioutil.ReadFile(n.NodesFile)
	if err != nil {
		n.Nodes = make(map[string]map[string]interface{})
		return
	}
	json.Unmarshal(data, &n.Nodes)
}

func (n *OrbitNode) SaveNodes() {
	n.NodesMu.Lock()
	defer n.NodesMu.Unlock()
	data, _ := json.MarshalIndent(n.Nodes, "", "  ")
	ioutil.WriteFile(n.NodesFile, data, 0644)
}

func (n *OrbitNode) LoadChain() {
	data, err := ioutil.ReadFile(n.ChainFile)
	if err != nil {
		n.Chain = []Block{}
		return
	}
	json.Unmarshal(data, &n.Chain)
}

func (n *OrbitNode) SaveChain() {
	n.ChainMu.Lock()
	defer n.ChainMu.Unlock()
	data, _ := json.MarshalIndent(n.Chain, "", "  ")
	ioutil.WriteFile(n.ChainFile, data, 0644)
}

func (n *OrbitNode) GetLast10BlockHash() string {
	n.ChainMu.RLock()
	defer n.ChainMu.RUnlock()
	
	length := len(n.Chain)
	if length == 0 {
		return ""
	}

	start := length - 10
	if start < 0 {
		start = 0
	}

	hashInput := ""
	for i := start; i < length; i++ {
		if h, ok := n.Chain[i]["hash"].(string); ok {
			hashInput += h
		}
	}
	hash := sha256.Sum256([]byte(hashInput))
	return hex.EncodeToString(hash[:])
}

func (n *OrbitNode) SendProofLoop() {
	for n.Running {
		if len(n.Chain) == 0 {
			time.Sleep(20 * time.Second)
			continue
		}
		last := n.Chain[len(n.Chain)-1]
		latestHash, _ := last["hash"].(string)
		proofHash := n.GetLast10BlockHash()

		payload := map[string]string{
			"node_id":     n.NodeID,
			"latest_hash": latestHash,
			"proof_hash":  proofHash,
		}
		body, _ := json.Marshal(payload)
		http.Post("https://oliver-butler-oasis-builder.trycloudflare.com/node_proof", "application/json", bytes.NewReader(body))

		time.Sleep(30 * time.Second)
	}
}
