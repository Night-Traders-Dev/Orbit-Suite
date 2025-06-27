package main

import (
	"fmt"
	"os"
	"os/signal"
	"strconv"

	"orbit_node/core"
	"orbit_node/network"
	"orbit_node/utils"
)

const explorerURL = "https://amateur-eric-receptors-casa.trycloudflare.com"

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: orbit_node <your-address> [port] [tunnel_url]")
		os.Exit(1)
	}

	userAddr := os.Args[1]
	port := 0
	if len(os.Args) > 2 {
		if p, err := strconv.Atoi(os.Args[2]); err == nil {
			port = p
		}
	}
	tunnel := ""
	if len(os.Args) > 3 {
		tunnel = os.Args[3]
	}

	node := core.NewOrbitNode(userAddr, port, tunnel)
	node.UID = utils.GenerateUID(node.NodeID, node.User, node.Port, node.TunnelURL)

	orbitAddr, err := utils.FetchOrbitAddress(explorerURL, node.UID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Could not fetch orbit address: %v\n", err)
		os.Exit(1)
	}
	node.Address = orbitAddr
	nodeFeeBalance, err := core.GetBalance("ORB.3C0738F00DE16991DDD5B506")

	node.SyncWithExplorer()
	node.RegisterNode()

	go network.StartHTTPServer(node)
	go network.RebroadcastIfNeeded(node)
	go network.PollForNewBlocks(node)
	go node.SendProofLoop()

	// Start TUI (blocks main thread)
	core.StartTUI(node)

	// graceful shutdown on Ctrl+C
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt)
	<-sig
	node.Running = false
}
