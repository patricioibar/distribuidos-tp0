package common

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"
)

const HeaderSize = 5

// Message types
const (
	TypeString byte = 0x01
)

type Message interface {
	Type() byte
	EncodeBody() ([]byte, error)
}

type StringMessage struct {
	Value string
}

func (m StringMessage) Type() byte { return TypeString }

func (m StringMessage) EncodeBody() ([]byte, error) {
	return []byte(m.Value), nil
}

func MessageFromBytes(msgType byte, bytes []byte) (Message, error) {
	switch msgType {
	case TypeString:
		return StringMessage{Value: string(bytes)}, nil
	default:
		return nil, fmt.Errorf("unknown message type: %x", msgType)
	}
}

func SendMessage(conn net.Conn, msg Message) error {
	body, err := msg.EncodeBody()
	if err != nil {
		return fmt.Errorf("encode error: %w", err)
	}

	header := make([]byte, HeaderSize)
	header[0] = msg.Type()
	binary.BigEndian.PutUint32(header[1:], uint32(len(body)))

	packet := append(header, body...)
	n, err := conn.Write(packet)
	if err != nil {
		return err
	}
	if n != len(packet) {
		return fmt.Errorf("failed to write complete message: wrote %d of %d bytes", n, len(packet))
	}
	return nil
}

func ReceiveMessage(conn net.Conn) (Message, error) {
	header := make([]byte, HeaderSize)
	if _, err := io.ReadFull(conn, header); err != nil {
		return nil, fmt.Errorf("error leyendo header: %w", err)
	}

	msgType := header[0]
	length := binary.BigEndian.Uint32(header[1:])

	body := make([]byte, length)
	if _, err := io.ReadFull(conn, body); err != nil {
		return nil, fmt.Errorf("error leyendo body: %w", err)
	}

	return MessageFromBytes(msgType, body)
}
