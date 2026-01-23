param(
  [Parameter(Mandatory = $true)]
  [int]$Port,

  [int]$TimeoutSeconds = 120,

  [string]$HostName = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)

while ([DateTime]::UtcNow -lt $deadline) {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $async = $client.BeginConnect($HostName, $Port, $null, $null)
    if ($async.AsyncWaitHandle.WaitOne(250) -and $client.Connected) {
      $client.Close()
      exit 0
    }
    $client.Close()
  } catch {
  }

  Start-Sleep -Milliseconds 250
}

exit 1

