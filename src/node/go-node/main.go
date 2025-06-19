//main.go:
package main

import (
	"orbit_node/core"
	"orbit_node/network"
	"os"
	"os/signal"
	"strconv"
)

func main() {
	if len(os.Args) < 2 {
		println("Usage: orbit_node <address> [port] [tunnel_url]")
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
	core.SyncWithExplorer(node)
	core.RegisterNode(node)

	go core.DisplayStats(node)
	go network.StartServer(node)
	go network.RebroadcastIfNeeded(node)

	ch := make(chan os.Signal, 1)
	signal.Notify(ch, os.Interrupt)
	<-ch
	node.Running = false
}
