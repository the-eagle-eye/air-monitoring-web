import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { usePolling } from './usePolling';

describe('usePolling', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    // Default: tab is visible.
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      get: () => false,
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it('invokes the callback on each interval', () => {
    const cb = jest.fn();
    renderHook(() => usePolling(cb, 1000));

    expect(cb).not.toHaveBeenCalled();
    act(() => jest.advanceTimersByTime(1000));
    expect(cb).toHaveBeenCalledTimes(1);
    act(() => jest.advanceTimersByTime(2000));
    expect(cb).toHaveBeenCalledTimes(3);
  });

  it('does not fire while the tab is hidden', () => {
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      get: () => true,
    });
    const cb = jest.fn();
    renderHook(() => usePolling(cb, 1000));

    act(() => jest.advanceTimersByTime(3000));
    expect(cb).not.toHaveBeenCalled();
  });

  it('does not start the interval when disabled', () => {
    const cb = jest.fn();
    renderHook(() => usePolling(cb, 1000, false));
    act(() => jest.advanceTimersByTime(5000));
    expect(cb).not.toHaveBeenCalled();
  });

  it('clears the interval on unmount', () => {
    const cb = jest.fn();
    const { unmount } = renderHook(() => usePolling(cb, 1000));
    act(() => jest.advanceTimersByTime(1000));
    expect(cb).toHaveBeenCalledTimes(1);
    unmount();
    act(() => jest.advanceTimersByTime(5000));
    expect(cb).toHaveBeenCalledTimes(1);
  });

  it('always calls the latest callback without resetting the interval', () => {
    const first = jest.fn();
    const second = jest.fn();
    const { rerender } = renderHook(({ fn }) => usePolling(fn, 1000), {
      initialProps: { fn: first },
    });

    act(() => jest.advanceTimersByTime(1000));
    expect(first).toHaveBeenCalledTimes(1);

    rerender({ fn: second });
    act(() => jest.advanceTimersByTime(1000));
    expect(second).toHaveBeenCalledTimes(1);
    expect(first).toHaveBeenCalledTimes(1);
  });
});
