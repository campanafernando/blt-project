# MinIO stopped publishing ready-made images; the pinned release is built from
# source. Same approach used in the ANA infrastructure.
FROM golang:1.24-alpine AS builder
ENV CGO_ENABLED=0
RUN go install -trimpath -ldflags="-s -w" github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z
RUN go install -trimpath -ldflags="-s -w" github.com/minio/mc@RELEASE.2025-08-13T08-35-41Z

FROM alpine:3.22
RUN apk add --no-cache ca-certificates curl
COPY --from=builder /go/bin/minio /go/bin/mc /usr/local/bin/
EXPOSE 9000 9001
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
