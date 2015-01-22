package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"math/rand"
	"net/http"
	"os"
	"runtime"
	"sync/atomic"
	"time"

	"github.com/dustin/go-humanize"
	"github.com/gorilla/websocket"
	"gopkg.in/vmihailenco/msgpack.v2"
)

type Config struct {
	URL      string
	Loops    int
	Interval int // msec
	Keep     int // sec
}

type RTT struct {
	Target    string // client address "ip:port"
	MsgNum    int32
	isStart   bool
	StartTime time.Time
	Sum       int64
	Min       float64
	Max       float64
}

type StressTestInfo struct {
	StartTime       time.Time
	AllSendByteSize int64
	AllRecvByteSize int64
	ConnExecTimeSum float64 // for avarage time
	ConnExecTimeMin float64
	ConnExecTimeMax float64
	ConnectionNum   int
	MessageRTT      RTT
	Config          *Config
}

func (st *StressTestInfo) send(ws *websocket.Conn, msg []map[string]interface{}) (err error) {
	packedMsg, err := msgpack.Marshal(msg)
	if err != nil {
		log.Printf("msgpack marshal error: %v", err)
		return err
	}
	if err = ws.WriteMessage(websocket.BinaryMessage, packedMsg); err != nil {
		log.Printf("write message: %v", err)
		return err
	}

	if st.MessageRTT.Target == ws.LocalAddr().String() {
		st.MessageRTT.isStart = true
		atomic.AddInt32(&st.MessageRTT.MsgNum, 1)
		st.MessageRTT.StartTime = time.Now()
	}

	atomic.AddInt64(&st.AllSendByteSize, int64(len(packedMsg)))
	return err
}

func (st *StressTestInfo) execScenarioTest() (err error) {
	var wsDialer = &websocket.Dialer{}
	var wsHeader = http.Header{"Origin": {st.Config.URL}}

	for i := 0; i < st.Config.Loops; i++ {
		url := st.Config.URL + "ws"

		startTime := time.Now()
		ws, _, err := wsDialer.Dial(url, wsHeader)
		if err != nil {
			log.Printf("new client: %v", err)
			break
		}
		// for RTT
		if i == 0 {
			st.MessageRTT.Target = ws.LocalAddr().String()
		}

		endTime := time.Now()
		diffTime := endTime.Sub(startTime).Seconds()
		st.ConnExecTimeSum += diffTime
		if st.ConnExecTimeMin > diffTime {
			st.ConnExecTimeMin = diffTime
		}
		if st.ConnExecTimeMax < diffTime {
			st.ConnExecTimeMax = diffTime
		}

		// count up ws connection
		st.ConnectionNum += 1

		go st.RecvWithPingPong(ws)
		go st.execScenario(ws)

		time.Sleep(time.Duration(st.Config.Interval) * time.Millisecond)
	}

	fmt.Printf("keep %dsec\n", st.Config.Keep)
	time.Sleep(time.Duration(st.Config.Keep) * time.Second)

	fmt.Println(fmt.Sprintf("test end. max connection is %d", st.ConnectionNum))

	return nil
}

var MsgpackSendData = map[string]interface{}{
	"a": 1,
}

func (st *StressTestInfo) execScenario(ws *websocket.Conn) {
	// scenario
	for {
		_data := MsgpackSendData
		var msg []map[string]interface{}
		msg = append(msg, _data)
		st.send(ws, msg)

		time.Sleep(time.Duration(rand.Intn(7)+3) * time.Second)
	}
}

func (st *StressTestInfo) RecvWithPingPong(ws *websocket.Conn) (err error) {
	for {
		msgType, r, err := ws.NextReader()
		if err != nil {
			ws.Close()
			break
		}

		if msgType != websocket.BinaryMessage {
			continue
		}

		var buf []byte
		buf, err = ioutil.ReadAll(r)
		if err != nil {
			ws.Close()
			break
		}
		atomic.AddInt64(&st.AllRecvByteSize, int64(len(buf)))

		if st.MessageRTT.isStart && st.MessageRTT.Target == ws.LocalAddr().String() {
			st.MessageRTT.isStart = false
			diffTime := time.Now().Sub(st.MessageRTT.StartTime).Seconds()
			atomic.AddInt64(&st.MessageRTT.Sum, int64(diffTime*1000))
			if st.MessageRTT.Min > diffTime {
				st.MessageRTT.Min = diffTime
			}
			if st.MessageRTT.Max < diffTime {
				st.MessageRTT.Max = diffTime
			}
		}
	}

	return nil
}

func (st *StressTestInfo) dumpInfo() {
	pid := os.Getpid()
	for {
		time.Sleep(time.Duration(10) * time.Second)
		now := time.Now()
		fmt.Printf("======= %v (elapsed: %v)\n", now, now.Sub(st.StartTime))
		fmt.Printf("tool's pid       : %d\n", pid)
		fmt.Printf("Target URL       : %s\n", st.Config.URL)
		fmt.Printf("Send Byte Size   : %s [byte] (%s)\n",
			humanize.Comma(int64(st.AllSendByteSize)), humanize.Bytes(uint64(st.AllSendByteSize)))
		fmt.Printf("Recive Byte Size : %s [byte] (%s)\n",
			humanize.Comma(st.AllRecvByteSize), humanize.Bytes(uint64(st.AllRecvByteSize)))
		fmt.Printf("Connection       : %d [conn]\n", st.ConnectionNum)
		fmt.Printf("Connect Time(avg): %.1f [ms]\n", st.ConnExecTimeSum/float64(st.ConnectionNum)*1000.)
		fmt.Printf("Connect Time(min): %.1f [ms]\n", st.ConnExecTimeMin*1000.)
		fmt.Printf("Connect Time(max): %.1f [ms]\n", st.ConnExecTimeMax*1000.)
		fmt.Printf("Message RTT (avg): %.1f [ms]\n", float64(st.MessageRTT.Sum)/float64(st.MessageRTT.MsgNum))
		fmt.Printf("Message RTT (min): %.1f [ms]\n", st.MessageRTT.Min*1000.)
		fmt.Printf("Message RTT (max): %.1f [ms]\n", st.MessageRTT.Max*1000.)
	}
}

func main() {
	var conf string
	flag.StringVar(&conf, "config", "", "config file path")

	flag.Parse()

	if runtime.GOMAXPROCS(2) > 1 {
		log.Println("not change GOMAXPROCS")
	}

	// for stress test
	st := new(StressTestInfo)
	config := new(Config)
	configFile, err := ioutil.ReadFile(conf)
	if err != nil {
		log.Println("open config file: ", err)
		return
	}
	if err = json.Unmarshal(configFile, config); err != nil {
		log.Println("parse config file: ", err)
		return
	}
	fmt.Println(config)

	st.Config = config
	st.ConnExecTimeMin = 999999.9
	st.MessageRTT.Min = 999999.9
	st.StartTime = time.Now()
	go st.dumpInfo()

	st.execScenarioTest()
}
