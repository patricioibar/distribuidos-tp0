package common

import (
	"bufio"
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
	MaxBatchSize  int
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
	defer c.conn.Close()

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

	shouldReturn := c.sendBatchedData()
	if shouldReturn {
		return
	}

	_, err2 := ReceiveMessage(c.conn)

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

	log.Infof("action: apuesta_enviada | result: success | dni: %s | numero: %s",
		os.Getenv(ENV_DOCUMENTO),
		os.Getenv(ENV_NUMERO),
	)
}

// sendBatchedData Reads the data file `/data/agency-<client_id>` and sends its content in batches
// of size `c.config.MaxBatchSize`. If an error occurs while sending a batch, it logs the error
// and returns true to indicate that the calling function should return immediately.
// If all data is sent successfully, it returns false.
func (c *Client) sendBatchedData() bool {
	filePath := fmt.Sprintf("/data/agency-%s", c.config.ID)
	file, err := os.Open(filePath)
	if err != nil {
		log.Errorf("action: open_file | result: fail | client_id: %v | error: %v", c.config.ID, err)
		return true
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	batch := []string{}
	batchSize := 0
	for scanner.Scan() {
		if batchSize >= c.config.MaxBatchSize {
			msg := StringListMessage{Values: batch}
			err := SendMessage(c.conn, msg)
			if err != nil {
				log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
					c.config.ID,
					err,
				)
				return true
			}
			batch = nil
			batchSize = 0
		}
		line := scanner.Text()
		batch = append(batch, line)
		batchSize++
	}
	if batchSize > 0 {
		msg := StringListMessage{Values: batch}
		err := SendMessage(c.conn, msg)
		if err != nil {
			log.Errorf("action: send_message | result: fail | client_id: %v | error: %v",
				c.config.ID,
				err,
			)
			return true
		}
	}
	return false
}
