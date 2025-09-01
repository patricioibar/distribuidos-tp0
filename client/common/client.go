package common

import (
	"fmt"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/op/go-logging"
)

var log = logging.MustGetLogger("log")

const ENV_NOMBRE = "NOMBRE"
const ENV_APELLIDO = "APELLIDO"
const ENV_DOCUMENTO = "DOCUMENTO"
const ENV_NACIMIENTO = "NACIMIENTO"
const ENV_NUMERO = "NUMERO"

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopAmount    int
	LoopPeriod    time.Duration
}

// Client Entity that encapsulates how
type Client struct {
	config  ClientConfig
	conn    net.Conn
	running bool
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config:  config,
		running: false,
	}
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGTERM)
	go func() {
		<-sig
		client.running = false
		client.conn.Close()
		log.Infof("action: socket_closed | result: success | client_id: %v", client.config.ID)
	}()

	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Criticalf(
			"action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	c.conn = conn
	return nil
}

// StartClientLoop Send messages to the client until some time threshold is met
func (c *Client) StartClientLoop() {
	// There is an autoincremental msgID to identify every message sent
	// Messages if the message amount threshold has not been surpassed

	c.running = true
	if !c.running {
		return
	}

	c.createClientSocket()

	err := SendMessage(c.conn, StringMessage{Value: c.config.ID})
	if err != nil {
		if !c.running {
			return
		}
		log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return
	}

	msg := c.createMessageFromEnvVars()

	err = SendMessage(c.conn, msg)
	if err != nil {
		if !c.running {
			return
		}
		log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
		return
	}

	msg2, err2 := ReceiveMessage(c.conn)
	c.conn.Close()

	if err2 != nil {
		if !c.running {
			return
		}
		log.Errorf("action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err2,
		)
		return
	}

	if msg == msg2 {
		log.Infof("action: apuesta_enviada | result: success | dni: %s | numero: %s",
			os.Getenv(ENV_DOCUMENTO),
			os.Getenv(ENV_NUMERO),
		)
	}
}

func (c *Client) createMessageFromEnvVars() Message {
	nombre := os.Getenv(ENV_NOMBRE)
	apellido := os.Getenv(ENV_APELLIDO)
	dni := os.Getenv(ENV_DOCUMENTO)
	nacimiento := os.Getenv(ENV_NACIMIENTO)
	numero := os.Getenv(ENV_NUMERO)
	msg := fmt.Sprintf("%s,%s,%s,%s,%s",
		nombre, apellido, dni, nacimiento, numero)
	log.Debugf("action: create_message | result: success | msg: %s", msg)
	return StringMessage{Value: msg}
}
