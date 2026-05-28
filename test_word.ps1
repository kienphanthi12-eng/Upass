try {
    $word = New-Object -ComObject Word.Application
    if ($word) {
        Write-Host "SUCCESS: Microsoft Word is installed via COM!"
        $word.Quit()
    } else {
        Write-Host "FAILED: New-Object returned null."
    }
} catch {
    Write-Host "FAILED: Error creating Word COM object: $_"
}
