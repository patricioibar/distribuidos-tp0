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
	TypeString     byte = 0x01
	TypeStringList byte = 0x02
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

type StringListMessage struct {
	Values []string
}

func (m StringListMessage) Type() byte { return TypeStringList }

func (m StringListMessage) EncodeBody() ([]byte, error) {
	buf := make([]byte, 0)
	for _, s := range m.Values {
		strBytes := []byte(s)
		size := uint32(len(strBytes))
		sizeBuf := make([]byte, 4)
		binary.BigEndian.PutUint32(sizeBuf, size)
		buf = append(buf, sizeBuf...)
		buf = append(buf, strBytes...)
	}
	return buf, nil
}

func stringListFromBytes(bytes []byte) (Message, error) {
	values := []string{}
	offset := 0
	for offset < len(bytes) {
		if offset+4 > len(bytes) {
			return nil, fmt.Errorf("invalid string list message: incomplete string size")
		}
		size := int(binary.BigEndian.Uint32(bytes[offset : offset+4]))
		offset += 4
		if offset+size > len(bytes) {
			return nil, fmt.Errorf("invalid string list message: incomplete string content")
		}
		str := string(bytes[offset : offset+size])
		values = append(values, str)
		offset += size
	}
	return StringListMessage{Values: values}, nil
}

func MessageFromBytes(msgType byte, bytes []byte) (Message, error) {
	switch msgType {
	case TypeString:
		return StringMessage{Value: string(bytes)}, nil
	case TypeStringList:
		return stringListFromBytes(bytes)
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
	totalWritten := 0
	for totalWritten < len(packet) {
		n, err := conn.Write(packet[totalWritten:])
		if err != nil {
			return err
		}
		totalWritten += n
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
