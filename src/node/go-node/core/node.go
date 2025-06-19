//core/node.go:
package core

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
//	"log"
	"math/rand"
	"net"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type Block map[string]interface{}

type OrbitNode struct {
	Address   string
	Port      int
	NodeID    string
	TunnelURL string
	ChainFile string
	NodesFile string
	Chain     []Block
	Nodes     map[string]map[string]interface{}
	ChainMu   sync.RWMutex
	NodesMu   sync.RWMutex
	Running   bool
}

const NodeDataDir = "node_data"

func NewOrbitNode(address string, port int, tunnel string) *OrbitNode {
	rand.Seed(time.Now().UnixNano())
	if port == 0 {
		port = getAvailablePort(5000, 5999)
	}
	os.MkdirAll(NodeDataDir, 0755)

	nodeID := fmt.Sprintf("Node%04d", rand.Intn(10000))
	nodesFile := filepath.Join(NodeDataDir, "nodes.json")
	chainFile := filepath.Join(NodeDataDir, fmt.Sprintf("orbit_chain.%s.json", nodeID))

	node := &OrbitNode{
		Address:   address,
		Port:      port,
		NodeID:    nodeID,
		TunnelURL: tunnel,
		ChainFile: chainFile,
		NodesFile: nodesFile,
		Chain:     []Block{},
		Nodes:     map[string]map[string]interface{}{},
		Running:   true,
	}
	loadChain(node)
	loadNodes(node)
	return node
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

func loadNodes(n *OrbitNode) {
	data, err := ioutil.ReadFile(n.NodesFile)
	if err == nil {
		json.Unmarshal(data, &n.Nodes)
	}
}

func SaveNodes(n *OrbitNode) {
	n.NodesMu.Lock()
	defer n.NodesMu.Unlock()
	data, _ := json.MarshalIndent(n.Nodes, "", "  ")
	ioutil.WriteFile(n.NodesFile, data, 0644)
}

func loadChain(n *OrbitNode) {
	data, err := ioutil.ReadFile(n.ChainFile)
	if err == nil {
		json.Unmarshal(data, &n.Chain)
	}
}

func SaveChain(n *OrbitNode) {
	n.ChainMu.Lock()
	defer n.ChainMu.Unlock()
	data, _ := json.MarshalIndent(n.Chain, "", "  ")
	ioutil.WriteFile(n.ChainFile, data, 0644)
}

func DisplayStats(n *OrbitNode) {
	for n.Running {
		uptime := n.Nodes[n.NodeID]["uptime"].(float64)
		trust := n.Nodes[n.NodeID]["trust"].(float64)
		fmt.Print("\033[H\033[2J")
		fmt.Println("\U0001F517 Orbit Node Dashboard")
		fmt.Println(strings.Repeat("=", 40))
		fmt.Printf("Node ID   : %s\n", n.NodeID)
		fmt.Printf("Address   : %s\n", n.Address)
		fmt.Printf("Port      : %d\n", n.Port)
		fmt.Printf("Trust     : %.4f\n", trust)
		fmt.Printf("Uptime    : %.4f\n", uptime)
		fmt.Printf("Chain Len : %d blocks\n", len(n.Chain))
		time.Sleep(10 * time.Second)
	}
}
