#!/bin/bash
set -x

INSTANCE="instances/jlopez/cdh/5.7.0/1" NOOP=1 fab start
INSTANCE="instances/jlopez/cdh/5.7.0/1" NOOP=1 fab stop
INSTANCE="instances/jlopez/cdh/5.7.0/1" NOOP=1 fab status

