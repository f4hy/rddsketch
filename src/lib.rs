//! rddsketch: a Rust DDSketch, exposed to Python via PyO3.
//!
//! The algorithm is [`sketches_ddsketch`]; this is a thin `#[pyclass]`
//! wrapper around it (input validation + PyO3 glue, no algorithm logic).
//!
//! `sketches_ddsketch::Config` doesn't expose the `relative_accuracy` it
//! was built from (only the derived `gamma`, and only `pub(crate)`), so
//! [`PyDDSketch`] tracks it separately and [`PyDDSketch::from_bytes`]
//! requires it as an explicit argument (it can't be recovered from the
//! encoded bytes alone without corrupting the standard wire format).

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use sketches_ddsketch::{Config, DDSketch as InnerSketch};

fn validate_relative_accuracy(relative_accuracy: f64) -> PyResult<()> {
    if !(relative_accuracy > 0.0 && relative_accuracy < 1.0) {
        return Err(PyValueError::new_err(format!(
            "relative_accuracy must be between 0 and 1 (exclusive), got {relative_accuracy}"
        )));
    }
    Ok(())
}

fn to_value_error<E: std::fmt::Display>(e: E) -> PyErr {
    PyValueError::new_err(e.to_string())
}

#[pyclass(name = "DDSketch")]
pub struct PyDDSketch {
    inner: InnerSketch,
    relative_accuracy: f64,
}

#[pymethods]
impl PyDDSketch {
    /// `max_num_bins` bounds store size; once exceeded, lowest-magnitude
    /// bins collapse first (matches `LogCollapsingLowestDenseDDSketch`).
    #[new]
    #[pyo3(signature = (relative_accuracy=0.01, max_num_bins=2048, min_value=1.0e-9))]
    fn new(relative_accuracy: f64, max_num_bins: u32, min_value: f64) -> PyResult<Self> {
        validate_relative_accuracy(relative_accuracy)?;
        if min_value.is_nan() || min_value <= 0.0 {
            return Err(PyValueError::new_err(format!(
                "min_value must be positive, got {min_value}"
            )));
        }
        if max_num_bins == 0 {
            return Err(PyValueError::new_err("max_num_bins must be positive"));
        }
        let config = Config::new(relative_accuracy, max_num_bins, min_value);
        Ok(Self {
            inner: InnerSketch::new(config),
            relative_accuracy,
        })
    }

    fn add(&mut self, value: f64) -> PyResult<()> {
        if !value.is_finite() {
            // NaN/inf would misclassify as zero or grow the store toward i32::MAX.
            return Err(PyValueError::new_err(format!(
                "value must be finite, got {value}"
            )));
        }
        self.inner.add(value);
        Ok(())
    }

    /// Value at quantile `q` in `[0, 1]`, or `None` if empty.
    fn quantile(&self, q: f64) -> PyResult<Option<f64>> {
        self.inner.quantile(q).map_err(to_value_error)
    }

    /// Alias matching `ddsketch.BaseDDSketch.get_quantile_value`.
    fn get_quantile_value(&self, q: f64) -> PyResult<Option<f64>> {
        self.quantile(q)
    }

    /// In-place merge; both sketches must share the same config.
    fn merge(&mut self, other: &PyDDSketch) -> PyResult<()> {
        self.inner.merge(&other.inner).map_err(to_value_error)
    }

    fn copy(&self) -> Self {
        Self {
            inner: self.inner.clone(),
            relative_accuracy: self.relative_accuracy,
        }
    }

    #[getter]
    fn count(&self) -> usize {
        self.inner.count()
    }

    #[getter]
    fn sum(&self) -> Option<f64> {
        self.inner.sum()
    }

    #[getter]
    fn avg(&self) -> Option<f64> {
        self.inner.sum().map(|s| s / self.inner.count() as f64)
    }

    #[getter]
    fn min(&self) -> Option<f64> {
        self.inner.min()
    }

    #[getter]
    fn max(&self) -> Option<f64> {
        self.inner.max()
    }

    #[getter]
    fn relative_accuracy(&self) -> f64 {
        self.relative_accuracy
    }

    /// DataDog's Java-compatible `DDSketchWithExactSummaryStatistics`
    /// binary encoding, unmodified.
    fn to_bytes<'py>(&self, py: Python<'py>) -> Bound<'py, PyBytes> {
        PyBytes::new(py, &self.inner.to_java_bytes())
    }

    /// `relative_accuracy` must match what the sketch was built with: it
    /// can't be recovered from the encoded bytes (see module docs).
    #[staticmethod]
    fn from_bytes(data: &[u8], relative_accuracy: f64) -> PyResult<Self> {
        validate_relative_accuracy(relative_accuracy)?;
        let inner = InnerSketch::from_java_bytes(data).map_err(to_value_error)?;
        Ok(Self {
            inner,
            relative_accuracy,
        })
    }

    /// Bin-store capacity, bounded by `2 * max_num_bins`.
    fn __len__(&self) -> usize {
        self.inner.length()
    }

    fn __repr__(&self) -> String {
        format!(
            "DDSketch(relative_accuracy={}, count={}, bins={})",
            self.relative_accuracy,
            self.inner.count(),
            self.inner.length()
        )
    }
}

#[pymodule]
fn _rddsketch(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDDSketch>()?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}

// Algorithm correctness is tested upstream in `sketches_ddsketch`; these
// cover wrapper validation/glue only. `to_bytes`/`from_bytes` need a GIL
// token, so they're covered by the pytest suite instead.
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_invalid_relative_accuracy() {
        assert!(PyDDSketch::new(0.0, 2048, 1e-9).is_err());
        assert!(PyDDSketch::new(1.0, 2048, 1e-9).is_err());
        assert!(PyDDSketch::new(-0.1, 2048, 1e-9).is_err());
        assert!(PyDDSketch::new(0.01, 2048, 1e-9).is_ok());
    }

    #[test]
    fn rejects_zero_bins_and_nonpositive_min_value() {
        assert!(PyDDSketch::new(0.01, 0, 1e-9).is_err());
        assert!(PyDDSketch::new(0.01, 2048, 0.0).is_err());
        assert!(PyDDSketch::new(0.01, 2048, -1.0).is_err());
    }

    #[test]
    fn rejects_non_finite_values() {
        let mut sketch = PyDDSketch::new(0.01, 2048, 1e-9).unwrap();
        assert!(sketch.add(f64::NAN).is_err());
        assert!(sketch.add(f64::INFINITY).is_err());
        assert!(sketch.add(f64::NEG_INFINITY).is_err());
        assert!(sketch.add(1.0).is_ok());
    }

    #[test]
    fn quantile_within_relative_accuracy() {
        let alpha = 0.01;
        let mut sketch = PyDDSketch::new(alpha, 2048, 1e-9).unwrap();
        for i in 1..=10_000 {
            sketch.add(i as f64).unwrap();
        }
        let median = sketch.quantile(0.5).unwrap().unwrap();
        let err = (median - 5_000.0).abs() / 5_000.0;
        assert!(err <= alpha * 1.5, "median={median} err={err}");
    }

    #[test]
    fn quantile_out_of_range_errors() {
        let sketch = PyDDSketch::new(0.01, 2048, 1e-9).unwrap();
        assert!(sketch.quantile(-0.1).is_err());
        assert!(sketch.quantile(1.1).is_err());
    }

    #[test]
    fn empty_sketch_quantile_is_none() {
        let sketch = PyDDSketch::new(0.01, 2048, 1e-9).unwrap();
        assert_eq!(sketch.quantile(0.5).unwrap(), None);
        assert_eq!(sketch.min(), None);
        assert_eq!(sketch.max(), None);
        assert_eq!(sketch.sum(), None);
        assert_eq!(sketch.count(), 0);
    }

    #[test]
    fn merge_requires_matching_config() {
        let mut a = PyDDSketch::new(0.01, 2048, 1e-9).unwrap();
        let b = PyDDSketch::new(0.02, 2048, 1e-9).unwrap();
        assert!(a.merge(&b).is_err());
    }

    #[test]
    fn merge_combines_counts() {
        let mut a = PyDDSketch::new(0.01, 2048, 1e-9).unwrap();
        let mut b = PyDDSketch::new(0.01, 2048, 1e-9).unwrap();
        for i in 1..=100 {
            a.add(i as f64).unwrap();
        }
        for i in 101..=200 {
            b.add(i as f64).unwrap();
        }
        a.merge(&b).unwrap();
        assert_eq!(a.count(), 200);
    }

    #[test]
    fn copy_is_independent() {
        let mut a = PyDDSketch::new(0.01, 2048, 1e-9).unwrap();
        a.add(1.0).unwrap();
        let b = a.copy();
        a.add(2.0).unwrap();
        assert_eq!(a.count(), 2);
        assert_eq!(b.count(), 1);
    }
}
