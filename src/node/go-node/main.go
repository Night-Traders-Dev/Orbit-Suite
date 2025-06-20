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

const explorerURL = "https://oliver-butler-oasis-builder.trycloudflare.com"

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
    fmt.Fprintf(os.Stderr, "🚨 could not fetch orbit address: %v\n", err)
    os.Exit(1)
  }
  node.Address = orbitAddr
  fmt.Printf("✅ Orbit Address: %s\n", node.Address)

  node.SyncWithExplorer()
  node.RegisterNode()

  go network.StartHTTPServer(node)
  go network.DisplayStats(node)
  go network.RebroadcastIfNeeded(node)
  go network.PollForNewBlocks(node)
  go node.SendProofLoop()

  // graceful shutdown on Ctrl+C
  sig := make(chan os.Signal, 1)
  signal.Notify(sig, os.Interrupt)
  <-sig
  node.Running = false
}