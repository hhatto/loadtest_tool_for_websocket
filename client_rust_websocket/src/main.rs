extern crate rustc_serialize;
extern crate rmp_serialize as msgpack;
extern crate websocket;
extern crate time;
use std::thread;
use std::collections::HashMap;
use std::time::Duration;
use std::sync::{mpsc, Arc, Mutex};
use websocket::{Message, Sender, Receiver};
use websocket::client::request::Url;
use websocket::client::Client;
use websocket::message::Type;
use websocket::stream::WebSocketStream;
use websocket::result::WebSocketError;
use websocket::sender as wsender;
use websocket::receiver as wreceiver;
use rustc_serialize::Encodable;
use msgpack::Encoder;

struct RTT {
    target: String,
    msg_num: i32,
    is_start: bool,
    start_time: time::Tm,
}

impl RTT {
    pub fn new() -> RTT {
        RTT {
            target: "".to_string(),
            msg_num: 0,
            is_start: false,
            start_time: time::now()
        }
    }
}

struct StressTestInfo {
    start_time: time::Tm,
}

fn sendloop(mut sender: wsender::Sender<WebSocketStream>,
            rx: mpsc::Receiver<Message>,
            rtt: Arc<Mutex<RTT>>) {
    loop {
        let mut h = HashMap::new();
        h.insert("a", 1);
        let custom_val = vec![h];
        let mut custom_buf = [0u8; 30];
        let _ = custom_val.encode(&mut Encoder::new(&mut &mut custom_buf[..]));
        //println!("custom encode: {:?}, {:?}", custom_buf, ret);

        let mut bbuf = vec![];
        for i in custom_buf.iter() {
            if *i == 0 {
                break;
            }
            bbuf.push(*i);
        }
        let bmsg = Message::binary(bbuf);
        let _ = match sender.send_message(&bmsg) {
            Ok(r) => r,
            Err(e) => {
                println!("Send error: {:?}", e);
                return;
            }
        };

        let _ = match rx.try_recv() {
            Ok(m) => {
                match m.opcode {
                    Type::Pong => {
                        sender.send_message(&m);
                        //println!("send PONG: {:?}", m);
                    }
                    _ => {
                        continue;
                    }
                }
            }
            Err(_) => {}
        };

        std::thread::sleep(Duration::from_millis(20));
    }
}

fn recvloop(mut receiver: wreceiver::Receiver<WebSocketStream>,
            tx: mpsc::Sender<Message>) {
    for msg in receiver.incoming_messages() {
        let msg: Message = match msg {
            Ok(m) => m,
            Err(WebSocketError::NoDataAvailable) => return, // connection close by server
            Err(e) => {
                println!("Receive Loop: {:?}", e);
                break;
            }
        };

        match msg.opcode {
            Type::Close => {
                let _ = tx.send(Message::close());
                return;
            }
            Type::Ping => {
                match tx.send(Message::pong(msg.payload)) {
                    Ok(()) => {
                        //println!("recv PING");
                    },
                    Err(e) => {
                        println!("Receive Loop: {:?}", e);
                        return;
                    }
                }
            }
            _ => {
                //println!("recv msg: {:?}", msg);
            },
        }
    }
}

fn main() {
    let url = Url::parse("ws://127.0.0.1:9000/ws").unwrap();
    println!("Connect to {}", url);

    let mut handles = vec![];
    let req = Client::connect(url).unwrap();
    let res = req.send().unwrap();

    res.validate().unwrap();
    println!("connected");

    let rtt = Arc::new(Mutex::new(RTT::new()));
    let (sender, receiver) = res.begin().split();
    let (tx, rx) = mpsc::channel();

    let send_loop = thread::spawn(move || sendloop(sender, rx, rtt.clone()));
    let recv_loop = thread::spawn(move || recvloop(receiver, tx));
    handles.push(send_loop);
    handles.push(recv_loop);

    for handle in handles {
        handle.join().unwrap();
    }
    println!("end");
}
