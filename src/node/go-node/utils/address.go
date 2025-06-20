package core

import (
  "bytes"
  "crypto/sha256"
  "encoding/hex"
  "encoding/json"
  "fmt"
  "io/ioutil"
  "net/http"
  "orbit_node/core"
)

// response shape from explorer
type getAddrResponse struct {
  Status  string `json:"status"`
  Address string `json:"address"`
}

// GenerateUID returns a deterministic UID for this node instance.
// It hashes NodeID, Address, Port and TunnelURL. As long as those inputs
// don’t change, you’ll get the same UID.
func (n *OrbitNode) GenerateUID() string {
  payload := fmt.Sprintf("%s|%s|%d|%s",
    n.NodeID,
    n.Address,
    n.Port,
    n.TunnelURL,
  )
  h := sha256.Sum256([]byte(payload))
  return hex.EncodeToString(h[:])
}

// FetchOrbitAddress calls your explorer’s /api/get_orbit_address endpoint,
// passing { "uid": "<your-uid>" } and returns the assigned orbit address.
func (n *OrbitNode) FetchOrbitAddress() (string, error) {
  uid := n.GenerateUID()
  reqBody, err := json.Marshal(map[string]string{"uid": uid})
  if err != nil {
    return "", fmt.Errorf("marshal uid: %w", err)
  }

  // TODO: move base URL into a const or config
  url := "https://oliver-butler-oasis-builder.trycloudflare.com/api/get_orbit_address"
  resp, err := http.Post(url, "application/json", bytes.NewReader(reqBody))
  if err != nil {
    return "", fmt.Errorf("POST get_orbit_address: %w", err)
  }
  defer resp.Body.Close()

  data, err := ioutil.ReadAll(resp.Body)
  if err != nil {
    return "", fmt.Errorf("read response: %w", err)
  }

  var out getAddrResponse
  if err := json.Unmarshal(data, &out); err != nil {
    return "", fmt.Errorf("unmarshal response: %w", err)
  }
  if out.Status != "success" {
    return "", fmt.Errorf("explorer error: %s", out.Status)
  }
  return out.Address, nil
}