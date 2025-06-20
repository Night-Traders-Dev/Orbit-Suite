package utils

import (
  "bytes"
  "crypto/sha256"
  "encoding/hex"
  "encoding/json"
  "fmt"
  "io/ioutil"
  "net/http"
)

// getAddrResponse mirrors the explorer’s JSON reply
type getAddrResponse struct {
  Status  string `json:"status"`
  Address string `json:"address"`
}

// GenerateUID deterministically hashes the inputs into a 64-hex string
func GenerateUID(nodeID, userAddr string, port int, tunnel string) string {
  raw := fmt.Sprintf("%s|%s|%d|%s", nodeID, userAddr, port, tunnel)
  sum := sha256.Sum256([]byte(raw))
  return hex.EncodeToString(sum[:])
}

// FetchOrbitAddress POSTs { uid } to /api/get_orbit_address
// and returns the explorer-assigned orbit address.
func FetchOrbitAddress(explorerBaseURL, uid string) (string, error) {
  body, _ := json.Marshal(map[string]string{"uid": uid})
  resp, err := http.Post(
    explorerBaseURL+"/api/get_orbit_address",
    "application/json",
    bytes.NewReader(body),
  )
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
    return "", fmt.Errorf("invalid JSON: %w", err)
  }
  if out.Status != "success" {
    return "", fmt.Errorf("explorer error: %s", out.Status)
  }
  return out.Address, nil
}