import { expect, test } from 'vitest';
import { increment } from '../../src/utils/numerical.js';

test('increment 1 to equal 2', () => {
  expect(increment(1)).toBe(2);
});
