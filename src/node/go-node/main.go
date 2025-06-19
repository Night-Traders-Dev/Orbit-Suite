// main.go
package main

import (
	"fmt"
	"os"
	"os/signal"
	"strconv"

	"orbit_node/core"
	"orbit_node/network"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: orbit_node <address> [port] [tunnel_url]")
		return
	}

	address := os.Args[1]
	port := 0
	if len(os.Args) > 2 {
		p, err := strconv.Atoi(os.Args[2])
		if err == nil {
			port = p
		}
	}
	tunnel := ""
	if len(os.Args) > 3 {
		tunnel = os.Args[3]
	}

	node := core.NewOrbitNode(address, port, tunnel)
	node.SyncWithExplorer()
	node.RegisterNode()

	go network.StartHTTPServer(node)
	go network.DisplayStats(node)
	go network.RebroadcastIfNeeded(node)
	go network.PollForNewBlocks(node)

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt)
	<-sig
	node.Running = false
}
