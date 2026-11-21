// Pattern probe, Go (standard library regexp, RE2). It applies NO rule of its own: it compiles the `native` string it is given and matches it against the input it is
// given (hex), exactly as the driver prepared them. Output, one line per case: `id|verdict|elapsed_ns`, verdict = compile_error | match | nomatch.
// The compile_error text goes to stderr only when VERBOSE=1. Usage: go run . cases.json
package main

import (
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"time"
)

type c struct {
	ID       string `json:"id"`
	Native   string `json:"native"`
	InputHex string `json:"input_hex"`
}

func main() {
	var cs []c
	b, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	if err := json.Unmarshal(b, &cs); err != nil {
		panic(err)
	}
	if len(cs) == 0 {
		fmt.Fprintln(os.Stderr, "no cases: refusing to produce an empty result")
		os.Exit(2)
	}
	for _, x := range cs {
		in, err := hex.DecodeString(x.InputHex)
		if err != nil {
			panic(err)
		}
		re, err := regexp.Compile(x.Native)
		if err != nil {
			if os.Getenv("VERBOSE") == "1" {
				fmt.Fprintf(os.Stderr, "%s: %v\n", x.ID, err)
			}
			fmt.Printf("%s|compile_error|0\n", x.ID)
			continue
		}
		t := time.Now()
		m := re.MatchString(string(in))
		e := time.Since(t).Nanoseconds()
		v := "nomatch"
		if m {
			v = "match"
		}
		fmt.Printf("%s|%s|%d\n", x.ID, v, e)
	}
}
