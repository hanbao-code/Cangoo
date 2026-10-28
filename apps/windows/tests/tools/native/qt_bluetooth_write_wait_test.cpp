// 编译时 PDM_WRITE_IO_STREAM_SOURCE 指向从最终补丁源原样提取的 writeIOStream。
#include <QtCore/qloggingcategory.h>
#include <QtCore/private/qfunctions_winrt_p.h>
#include <robuffer.h>
#include <windows.storage.streams.h>
#include <wrl.h>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <memory>
#include <thread>

using namespace Microsoft::WRL;
using namespace Microsoft::WRL::Wrappers;
using namespace ABI::Windows::Foundation;
using namespace ABI::Windows::Storage::Streams;
using Operation = IAsyncOperationWithProgress<UINT32, UINT32>;
using Handler = IAsyncOperationWithProgressCompletedHandler<UINT32, UINT32>;
using Progress = IAsyncOperationProgressHandler<UINT32, UINT32>;

static void checked(bool value, int line)
{
    if (!value) {
        std::fprintf(stderr, "CHECK FAILED: %d\n", line);
        ExitProcess(1);
    }
}
#define check(value) checked(bool(value), __LINE__)

Q_LOGGING_CATEGORY(QT_BT_WINDOWS, "qt.bluetooth.wait.test")
static struct { ComPtr<IBufferFactory> bufferFactory; } globals, *g = &globals;
static bool failWait = false;
static HANDLE lastWaitedEvent = nullptr;
static DWORD testWait(HANDLE event, DWORD timeout)
{
    lastWaitedEvent = event;
    if (failWait) {
        SetLastError(ERROR_INVALID_HANDLE);
        return WAIT_FAILED;
    }
    // 超时只用于让回归死锁变成有限失败，产品代码仍传 INFINITE。
    check(timeout == INFINITE);
    const DWORD result = WaitForSingleObject(event, 5000);
    check(result == WAIT_OBJECT_0);
    return result;
}
#define WaitForSingleObject testWait
#include PDM_WRITE_IO_STREAM_SOURCE
#undef WaitForSingleObject

class TestOperation final : public RuntimeClass<RuntimeClassFlags<WinRtClassicComMix>, Operation, IAsyncInfo, FtmBase>
{
public:
    InspectableClass(L"Cangoo.TestWriteOperation", BaseTrust);
public:
    AsyncStatus finalStatus = Completed;
    bool immediate = false;
    bool failRegistration = false;
    std::atomic<AsyncStatus> status{Started};
    std::atomic<unsigned> statusReads{0};
    std::atomic<unsigned> resultReads{0};
    std::atomic<unsigned> cancels{0};
    std::atomic<unsigned> closes{0};
    ComPtr<IBuffer> buffer;
    ComPtr<Handler> handler;
    std::thread worker;

    HRESULT STDMETHODCALLTYPE put_Completed(Handler *value) override
    {
        if (failRegistration)
            return E_ACCESSDENIED;
        handler = value;
        ComPtr<IAgileObject> agile;
        check(SUCCEEDED(handler.As(&agile)));
        if (immediate) {
            status = finalStatus;
            return handler->Invoke(this, finalStatus);
        }
        ComPtr<IStream> marshaled;
        check(SUCCEEDED(CoMarshalInterThreadInterfaceInStream(__uuidof(Handler), value, &marshaled)));
        IStream *stream = marshaled.Detach();
        worker = std::thread([this, stream] {
            check(SUCCEEDED(RoInitialize(RO_INIT_MULTITHREADED)));
            ComPtr<Handler> remote;
            check(SUCCEEDED(CoGetInterfaceAndReleaseStream(stream, IID_PPV_ARGS(&remote))));
            std::this_thread::sleep_for(std::chrono::milliseconds(80));
            status = finalStatus;
            check(SUCCEEDED(remote->Invoke(this, finalStatus)));
            RoUninitialize();
        });
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE get_Completed(Handler **value) override { return handler.CopyTo(value); }
    HRESULT STDMETHODCALLTYPE put_Progress(Progress *) override { return S_OK; }
    HRESULT STDMETHODCALLTYPE get_Progress(Progress **value) override { *value = nullptr; return S_OK; }
    HRESULT STDMETHODCALLTYPE GetResults(UINT32 *value) override
    {
        ++resultReads;
        check(status == Completed);
        return buffer->get_Length(value);
    }
    HRESULT STDMETHODCALLTYPE get_Id(UINT32 *value) override { *value = 1; return S_OK; }
    HRESULT STDMETHODCALLTYPE get_Status(AsyncStatus *value) override
    {
        ++statusReads;
        *value = status;
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE get_ErrorCode(HRESULT *value) override
    {
        *value = status == Canceled ? E_ABORT : E_ACCESSDENIED;
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE Cancel() override { ++cancels; return S_OK; }
    HRESULT STDMETHODCALLTYPE Close() override { ++closes; return S_OK; }
};

class TestStream final : public RuntimeClass<RuntimeClassFlags<WinRt>, IOutputStream>
{
public:
    InspectableClass(L"Cangoo.TestWriteStream", BaseTrust);
public:
    ComPtr<TestOperation> op = Make<TestOperation>();
    bool failWrite = false;
    HRESULT STDMETHODCALLTYPE WriteAsync(IBuffer *buffer, Operation **value) override
    {
        if (failWrite)
            return E_FAIL;
        op->buffer = buffer;
        ComPtr<Windows::Storage::Streams::IBufferByteAccess> access;
        check(SUCCEEDED(op->buffer.As(&access)));
        byte *bytes = nullptr;
        check(SUCCEEDED(access->Buffer(&bytes)));
        UINT32 length = 0;
        check(SUCCEEDED(buffer->get_Length(&length)));
        check(length == 0 || (length == 4 && memcmp(bytes, "test", 4) == 0));
        if (op->immediate)
            op->status = op->finalStatus;
        return op.CopyTo(value);
    }
    HRESULT STDMETHODCALLTYPE FlushAsync(IAsyncOperation<bool> **) override { return E_NOTIMPL; }
};

static void run(AsyncStatus result, bool immediate, bool registrationFailure = false,
                bool writeFailure = false, bool waitFailure = false, bool empty = false)
{
    auto stream = Make<TestStream>();
    stream->op->finalStatus = result;
    stream->op->immediate = immediate;
    stream->op->failRegistration = registrationFailure;
    stream->failWrite = writeFailure;
    failWait = waitFailure;
    lastWaitedEvent = nullptr;
    const bool failed = registrationFailure || writeFailure || waitFailure;
    const auto actual = writeIOStream(stream, "test", empty ? 0 : 4);
    check(actual == (!failed && result == Completed ? (empty ? 0 : 4) : -1));
    if (stream->op->worker.joinable())
        stream->op->worker.join();
    check(stream->op->statusReads == (failed ? 0u : 1u));
    check(stream->op->resultReads == (!failed && result == Completed ? 1u : 0u));
    check(stream->op->closes == (!failed && result != Completed ? 1u : 0u));
    check(stream->op->cancels == ((registrationFailure || waitFailure) ? 1u : 0u));
    stream.Reset();
    if (lastWaitedEvent) {
        DWORD flags = 0;
        check(!GetHandleInformation(lastWaitedEvent, &flags));
        check(GetLastError() == ERROR_INVALID_HANDLE);
    }
    failWait = false;
}

int main()
{
    check(SUCCEEDED(RoInitialize(RO_INIT_SINGLETHREADED)));
    check(SUCCEEDED(GetActivationFactory(
            HString::MakeReference(RuntimeClass_Windows_Storage_Streams_Buffer).Get(), &g->bufferFactory)));
    run(Completed, false);
    for (const auto state : {Completed, Error, Canceled}) {
        run(state, true);
        run(state, false);
    }
    run(Completed, true, false, false, false, true);
    run(Completed, false, true);
    run(Completed, false, false, true);
    run(Completed, false, false, false, true);
    g->bufferFactory.Reset();
    RoUninitialize();
    std::puts("PASS: original patched writeIOStream; STA/MTA marshaling; early/late completion; success/error/cancel; registration/write/wait failure; empty buffer; event release");
}
