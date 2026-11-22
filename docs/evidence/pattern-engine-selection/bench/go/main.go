// Bench runner, Go (standard library regexp, RE2). One case per process so the peak resident memory belongs to the case.
// Input: a JSON file {native, input_hex, compiles, matches}. Output, one line: compile_ns_min|match_ns_median|vmhwm_kb|0   (vmhwm = the process peak, read from /proc/self/status).
// Usage: go run . case.json
package main

import (
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"runtime"
	"sort"
	"strings"
	"time"
)

type c struct {
	Native   string `json:"native"`
	InputHex string `json:"input_hex"`
	Compiles int    `json:"compiles"`
	Matches  int    `json:"matches"`
}

func status(key string) int {
	b, _ := os.ReadFile("/proc/self/status")
	for _, l := range strings.Split(string(b), "\n") {
		if strings.HasPrefix(l, key+":") {
			var n int
			fmt.Sscanf(strings.Fields(l)[1], "%d", &n)
			return n
		}
	}
	return 0
}

func main() {
	var x c
	b, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	if err := json.Unmarshal(b, &x); err != nil || x.Compiles < 1 || x.Matches < 1 {
		fmt.Fprintln(os.Stderr, "bad case: refusing to produce a result")
		os.Exit(2)
	}
	in, _ := hex.DecodeString(x.InputHex)
	v := string(in)
	regexp.MustCompile("a").MatchString(v) // warm up
	runtime.GC()
	rss0 := status("VmRSS")
	if err := os.WriteFile("/proc/self/clear_refs", []byte("5"), 0o200); err != nil {
		fmt.Fprintln(os.Stderr, "INCOMPLETE: /proc/self/clear_refs is not writable:", err)
		os.Exit(4)
	}
	var re *regexp.Regexp
	cmin := int64(1 << 62)
	for i := 0; i < x.Compiles; i++ {
		t := time.Now()
		r, err := regexp.Compile(x.Native)
		e := time.Since(t).Nanoseconds()
		if err != nil {
			fmt.Fprintln(os.Stderr, "compile error:", err)
			os.Exit(3)
		}
		re = r
		if e < cmin {
			cmin = e
		}
	}
	ms := []int64{}
	for i := 0; i < x.Matches; i++ {
		t := time.Now()
		re.MatchString(v)
		ms = append(ms, time.Since(t).Nanoseconds())
	}
	sort.Slice(ms, func(i, j int) bool { return ms[i] < ms[j] })
	peak := status("VmHWM") - rss0
	if peak < 0 {
		peak = 0
	}
	fmt.Printf("%d|%d|%d|0\n", cmin, ms[len(ms)/2], peak)
}
