# protocol-ri Introduction

This document describes the mPlane Protocol, which is implemented by the reference implementation in this module (protocol-ri). The mPlane Protocol provides control and data interchange for passive and active network measurement tasks. It is built around a simple workflow in which Capabilities are published by Components, which can accept Specifications for measurements based on these Capabilities, and provide Results, either inline or via an indirect export mechanism negotiated using the protocol. 

The reference impelementation in the module is the normative reference for the mPlane protocol until such time as it is deemed stable by the mPlane consortium (presently scheduled for November 2014), at which time the document derived from this README will contain the normative reference for the protocol.

Measurement statements are fundamentally based on schemas divided into Parameters, representing information required to run a measurement or query; and Result Columns, the information produced by the measurement or query. Measurement interoperability is provided at the element level; that is, measurements containing the same Parameters and Result Columns are considered to be of the same type and therefore comparable.

This document defines the terminology for the mPlane protocol in section 2, describes the architecture used by the protocol in section 3, defines the Information Model in detail in section 4 and bindings to session protocols in section 5. Section 6 outlines concrete workflows which can be used by the protocol.

Section 7 outlines additional features of the Reference Implementation which, while not providing a normative reference for the mPlane protocol 

# Terminology

### Component

### Client

### Supervisor

### Message

### Primitive

### Element

### Element Registry

### Constraint

### Verb

### Parameter

### Metadata

### Result Column

### Statement

### Capability

### Specification

### Result

### Notification

### Receipt

### Redemption

### Withdrawal

### Interrupt

### Indirection

### Exception

# Architecture

## Principles

## Components and Clients

## Supervisors and Federation

# Protocol Information Model

## Statements

## Capabilities

## Specifications

## Results

## Receipts and Redemptions

## Indirections

# Session Protocols

## JSON representation

## mPlane over HTTPS

## mPlane over SSH

# Workflows in mPlane

# Reference Implementation Features

## Core Classes

## mPlane Client Shell

The mPlane client shell (in the mplane.client module) is a generic command-line shell for 

## ICMP Ping Application

### Component Server

### Supervisor

