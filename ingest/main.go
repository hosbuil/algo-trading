package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/gorilla/websocket"
	"log"
	"os"
	"os/signal"
	"strings"
	"time"
)

type candle struct {
	Kind string `json:"e"`
	K    struct {
		Time   int64  `json:"t"`
		Close  string `json:"c"`
		Closed bool   `json:"x"`
	} `json:"k"`
}

func main() {
	symbol := flag.String("symbol", "btcusdt", "Binance spot symbol")
	out := flag.String("out", "data/bars.csv", "new output CSV")
	flag.Parse()
	f, err := os.OpenFile(*out, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0644)
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()
	w := bufio.NewWriterSize(f, 1<<20)
	defer w.Flush()
	fmt.Fprintln(w, "timestamp,close")
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()
	var last int64
	delay := time.Second
	for ctx.Err() == nil {
		c, _, err := websocket.DefaultDialer.DialContext(ctx, "wss://stream.binance.com:9443/ws/"+strings.ToLower(*symbol)+"@kline_1m", nil)
		if err == nil {
			done := make(chan struct{})
			go func() {
				select {
				case <-ctx.Done():
					c.Close()
				case <-done:
				}
			}()
			c.SetReadLimit(1 << 20)
			for {
				c.SetReadDeadline(time.Now().Add(90 * time.Second))
				_, b, e := c.ReadMessage()
				if e != nil {
					err = e
					break
				}
				var v candle
				if json.Unmarshal(b, &v) != nil || !v.K.Closed || v.K.Time <= last {
					continue
				}
				if last > 0 && v.K.Time != last+60000 {
					log.Printf("GAP: %d -> %d; backfill required", last, v.K.Time)
				}
				if _, e = fmt.Fprintf(w, "%d,%s\n", v.K.Time, v.K.Close); e != nil {
					log.Fatal(e)
				}
				if e = w.Flush(); e != nil {
					log.Fatal(e)
				}
				last = v.K.Time
				delay = time.Second
			}
			close(done)
			c.Close()
		}
		if ctx.Err() != nil {
			break
		}
		log.Printf("reconnect after %s: %v", delay, err)
		select {
		case <-ctx.Done():
		case <-time.After(delay):
		}
		if delay < 30*time.Second {
			delay *= 2
		}
	}
}
